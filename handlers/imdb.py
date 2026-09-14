import os
import re
import asyncio
import logging
from io import BytesIO
from bs4 import BeautifulSoup
import aiohttp
import httpx

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

# ── LOGGING & CONFIG ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# നിങ്ങളുടെ info.py ഫയലിൽ ഉള്ളതുപോലെ ആവശ്യാനുസരണം മാറ്റാം
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")
LONG_IMDB_DESCRIPTION = False

# ഫയൽ ക്രാഷ് ആവാതിരിക്കാനുള്ള ഡിഫോൾട്ട് ക്യാപ്ഷൻ ടെംപ്ലേറ്റ്
IMDB_TEMPLATE = """
🎬 **{title}** ({year})
⭐ **Rating:** {rating}/10 ({votes} votes)
🎭 **Genre:** {genre_tags}
🌐 **Language:** {language_tags}
👤 **Director:** {director}
👥 **Cast:** {cast}

📝 **Plot:** {plot}
"""

def list_to_str(lst):
    """ഒരു ലിസ്റ്റിനെ കോമയിട്ട സസ്റ്റിങ് ആക്കി മാറ്റുന്നു"""
    if not lst:
        return "N/A"
    return ", ".join(str(x) for x in lst if x)

# ── IMDBIO CHECK ─────────────────────────────────────────────────────────
try:
    import imdbio as _imdbio
    from imdbio.exceptions import ImdbioError as _ImdbioError
    IMDBIO_AVAILABLE = True
except ImportError:
    IMDBIO_AVAILABLE = False

class _OmdbFakeMovie:
    """Wraps an OMDb search-result dict to match Cinemagoer's object interface."""
    def __init__(self, m):
        self._m = m
        self.movieID = f"omdb_{m.get('imdbID')}"
    def get(self, k, default=None):
        _map = {'title': 'Title', 'year': 'Year', 'kind': 'Type'}
        return self._m.get(_map.get(k, k), default)

class _ImdbioFakeMovie:
    """Wraps an imdbio MovieBriefInfo search result to match Cinemagoer's object interface."""
    def __init__(self, m):
        self._m = m
        self.movieID = f"imdbio_{m.imdb_id}"
    def get(self, k, default=None):
        if k == 'title': return self._m.title or default
        if k == 'year': return self._m.year or default
        if k == 'kind': return self._m.kind or default
        return default

def _names(people):
    """imdbio Person ഒബ്ജക്റ്റുകളിൽ നിന്ന് പേരുകൾ വേർതിരിക്കുന്നു."""
    try:
        names = [p.name for p in people if getattr(p, "name", None)]
    except (TypeError, AttributeError):
        return "N/A"
    return list_to_str(names) if names else "N/A"

def _cat(m, key):
    try:
        return _names(m.categories.get(key, []))
    except (AttributeError, TypeError):
        return "N/A"

async def _imdbio_search(title, year=None, bulk=False):
    if not IMDBIO_AVAILABLE: return None
    try:
        result = await asyncio.to_thread(_imdbio.search_title, title, year=year)
    except Exception as e:
        logger.warning(f"imdbio search error: {e}")
        return None
    if not result or not result.titles: return None
    if bulk: return [_ImdbioFakeMovie(t) for t in result.titles[:10]]
    return await _imdbio_get_details(result.titles[0].imdb_id)

async def _imdbio_get_details(imdb_id):
    if not IMDBIO_AVAILABLE: return None
    if isinstance(imdb_id, str) and imdb_id.startswith("imdbio_"):
        imdb_id = imdb_id[len("imdbio_"):]
    try:
        m = await asyncio.to_thread(_imdbio.get_movie, imdb_id)
    except Exception as e:
        logger.warning(f"imdbio details error: {e}")
        return None
    if not m: return None

    plot = m.plot or "N/A"
    if not LONG_IMDB_DESCRIPTION and plot and plot != "N/A" and len(plot) > 800:
        plot = plot[:800] + "..."

    try: cast = _names(m.categories.get("cast", []))
    except Exception: cast = _names(m.stars) if getattr(m, "stars", None) else "N/A"

    return {
        'title': m.title or "N/A",
        'votes': str(m.votes) if m.votes else "N/A",
        "aka": list_to_str(m.title_akas) if getattr(m, "title_akas", None) else "N/A",
        'localized_title': m.title_localized or m.title or "N/A",
        'kind': "tv series" if m.is_series() else "movie",
        "imdb_id": m.imdb_id or "N/A",
        "cast": cast,
        "runtime": f"{m.duration} min" if getattr(m, "duration", None) else "N/A",
        "countries": list_to_str(m.countries) if getattr(m, "countries", None) else "N/A",
        "certificates": m.mpaa or m.certificate or "N/A",
        "languages": list_to_str(m.languages_text or m.languages) if (getattr(m, "languages_text", None) or getattr(m, "languages", None)) else "N/A",
        "director": _names(m.directors) if getattr(m, "directors", None) else "N/A",
        "writer": _cat(m, "writer"),
        'release_date': m.release_date or "N/A",
        'year': str(m.year) if m.year else "N/A",
        'genres': list_to_str(m.genres) if getattr(m, "genres", None) else "N/A",
        'poster': _hq_poster(m.cover_url),
        'plot': plot,
        'rating': str(m.rating) if m.rating else "N/A",
        'url': m.url or f"https://imdb.com{m.imdb_id}/",
        'trailers': list(m.trailers) if getattr(m, "trailers", None) else [],
        '_source': 'imdbio',
    }

def _hq_poster(url):
    if not url or url == "N/A": return None
    return re.sub(r'\._[A-Z0-9,]+_(?=\.\w+$)', '', url)

async def fetch_poster_bytes(url):
    if not url: return None
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"poster download failed: {e}")
        return None

async def _omdb_search(title, year=None, bulk=False):
    if not OMDB_API_KEY: return None
    try:
        params = {"apikey": OMDB_API_KEY, "s": title}
        if year: params["y"] = year
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://omdbapi.com", params=params)
            data = resp.json()
    except Exception: return None
    if data.get("Response") != "True": return None
    results = data.get("Search", [])
    if not results: return None
    if bulk: return [_OmdbFakeMovie(r) for r in results[:10]]
    return await _omdb_get_details(results[0]["imdbID"])

async def _omdb_get_details(imdb_id):
    if not OMDB_API_KEY: return None
    if isinstance(imdb_id, str) and imdb_id.startswith("omdb_"):
        imdb_id = imdb_id[len("omdb_"):]
    try:
        params = {"apikey": OMDB_API_KEY, "i": imdb_id, "plot": "short"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://omdbapi.com", params=params)
            m = resp.json()
    except Exception: return None
    if not m or m.get("Response") != "True": return None

    def _split(field):
        v = m.get(field)
        return list_to_str([p.strip() for p in v.split(",")]) if v and v != "N/A" else "N/A"

    return {
        'title': m.get("Title", "N/A"), 'votes': m.get("imdbVotes", "N/A"), "aka": "N/A",
        'localized_title': m.get("Title", "N/A"), 'kind': "movie", "imdb_id": m.get("imdbID", "N/A"),
        "cast": _split("Actors"), "runtime": m.get("Runtime", "N/A"), "countries": _split("Country"),
        "certificates": m.get("Rated", "N/A"), "languages": _split("Language"), "director": _split("Director"),
        "writer": _split("Writer"), 'release_date': m.get("Released", "N/A"), 'year': m.get("Year", "N/A"),
        'genres': _split("Genre"), 'poster': _hq_poster(m.get("Poster")), 'plot': m.get("Plot", "N/A"),
        'rating': m.get("imdbRating", "N/A"), 'url': f"https://imdb.com{m.get('imdbID')}/",
        'trailers': [], '_source': 'omdb',
    }

async def get_poster(query, bulk=False, id=False, file=None):
    if id:
        result = await _imdbio_get_details(query)
        return result if result else await _omdb_get_details(query)

    query = query.strip().lower()
    title = query
    year = re.findall(r'[1-2]\d{3}$', query)
    if year:
        year = list_to_str(year[:1])
        title = query.replace(year, "").strip()
    
    result = await _imdbio_search(title, year=year, bulk=bulk)
    return result if result else await _omdb_search(title, year=year, bulk=bulk)



# ── COMMAND HANDLERS ─────────────────────────────────────────────────────

@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply('🔍 Searching...')
        r, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await k.edit("❌ No results found on IMDb/OMDb.")
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year') or 'N/A'}",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await k.edit('🎬 Here is what I found:', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('Give me a movie / series Name')

async def _send_photo_bytes_or_text(message, poster_url, caption, btn):
    raw = await fetch_poster_bytes(poster_url)
    if raw:
        try:
            photo = BytesIO(raw)
            photo.name = "poster.jpg"
            await message.reply_photo(photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
            return
        except Exception as e:
            logger.exception(e)
    await message.reply(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)

@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    i, movie_id = quer_y.data.split('#')
    data = await get_poster(query=movie_id, id=True)
    
    if not data:
        await quer_y.answer("❌ Could not fetch details.", show_alert=True)
        return

    def _tags(field):
        if not field or field == "N/A":
            return "N/A"
        return " ".join(f"#{p.strip().replace(' ', '_')}" for p in field.split(",") if p.strip())

    _aka_line = f"\n📝 Also Known As: {data['aka']}" if data.get("aka") and data["aka"] != "N/A" else ""
    _genre_tags = _tags(data["genres"])
    _language_tags = _tags(data["languages"])
    _country_tags = _tags(data["countries"])

    btn = [
        [
            InlineKeyboardButton(
                text=f"🔗 {data.get('title')} on IMDb",
                url=data['url'],
            )
        ]
    ]
    if data.get("trailers"):
        btn.append([
            InlineKeyboardButton(
                text="▶️ Watch Trailer",
                url=data["trailers"][-1],
            )
        ])
        
    caption = IMDB_TEMPLATE.format(
        query=data['title'],
        title=data['title'],
        votes=data['votes'],
        aka=data["aka"],
        aka_line=_aka_line,
        seasons=data.get("seasons", "N/A"),
        box_office=data['box_office'],
        localized_title=data['localized_title'],
        kind=data['kind'],
        imdb_id=data["imdb_id"],
        cast=data["cast"],
        runtime=data["runtime"],
        countries=data["countries"],
        country_tags=_country_tags,
        certificates=data["certificates"],
        languages=data["languages"],
        language_tags=_language_tags,
        director=data["director"],
        writer=data["writer"],
        producer=data.get("producer", "N/A"),
        composer=data.get("composer", "N/A"),
        cinematographer=data.get("cinematographer", "N/A"),
        music_team=data.get("music_team", "N/A"),
        distributors=data.get("distributors", "N/A"),
        release_date=data['release_date'],
        year=data['year'],
        genres=data['genres'],
        genre_tags=_genre_tags,
        poster=data['poster'],
        plot=data['plot'],
        rating=data['rating'],
        url=data['url']
    )
    
    if data.get('poster') and data['poster'] != "N/A":
        try:
            await quer_y.message.reply_photo(photo=data['poster'], caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = data.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            try:
                await quer_y.message.reply_photo(photo=poster, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
            except Exception as e:
                logger.exception(e)
                await _send_photo_bytes_or_text(quer_y.message, data['poster'], caption, btn)
        except Exception as e:
            logger.exception(e)
            await _send_photo_bytes_or_text(quer_y.message, data['poster'], caption, btn)
        await quer_y.message.delete()
    else:
        await quer_y.message.edit(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    await quer_y.answer()
