from bs4 import BeautifulSoup
import aiohttp
import httpx



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
        if k == 'title':
            return self._m.title or default
        if k == 'year':
            return self._m.year or default
        if k == 'kind':
            return self._m.kind or default
        return default


def _names(people):
    """Turn a list of imdbio Person/CastMember objects into a joined name string."""
    try:
        names = [p.name for p in people if getattr(p, "name", None)]
    except (TypeError, AttributeError):
        return "N/A"
    return list_to_str(names) if names else "N/A"


def _cat(m, key):
    """Safely pull a named category (writer, producer, ...) off an imdbio MovieDetail."""
    try:
        return _names(m.categories.get(key, []))
    except (AttributeError, TypeError):
        return "N/A"


async def _imdbio_search(title, year=None, bulk=False):
    """Search movies/shows via imdbio (no API key required)."""
    if not IMDBIO_AVAILABLE:
        return None
    try:
        result = await asyncio.to_thread(_imdbio.search_title, title, year=year)
    except _ImdbioError as e:
        logger.warning(f"imdbio search error: {e}")
        return None
    except TypeError as e:
        # known upstream quirk in some imdbio releases (internal lru_cache hashing
        # occasionally chokes on certain inputs) — not fixable on our side, falls
        # back to OMDb automatically, so just a quiet warning instead of a full trace
        logger.warning(f"imdbio search skipped (upstream bug): {e}")
        return None
    except Exception as e:
        logger.exception(f"imdbio search unexpected error: {e}")
        return None

    if not result or not result.titles:
        return None
    if bulk:
        return [_ImdbioFakeMovie(t) for t in result.titles[:10]]
    return await _imdbio_get_details(result.titles[0].imdb_id)

async def _imdbio_get_details(imdb_id):
    """Fetch full details via imdbio by IMDb ID."""
    if not IMDBIO_AVAILABLE:
        return None
    if isinstance(imdb_id, str) and imdb_id.startswith("imdbio_"):
        imdb_id = imdb_id[len("imdbio_"):]
    try:
        m = await asyncio.to_thread(_imdbio.get_movie, imdb_id)
    except _ImdbioError as e:
        logger.warning(f"imdbio details error: {e}")
        return None
    except Exception as e:
        logger.exception(f"imdbio details unexpected error: {e}")
        return None
    if not m:
        return None

    plot = m.plot or "N/A"
    if not LONG_IMDB_DESCRIPTION and plot and plot != "N/A" and len(plot) > 800:
        plot = plot[:800] + "..."

    try:
        seasons = len(m.info_series.display_seasons) if getattr(m, "info_series", None) else None
    except (AttributeError, TypeError):
        seasons = None

    try:
        cast = _names(m.categories.get("cast", []))
        if cast == "N/A":
            cast = _names(m.stars)
    except (AttributeError, TypeError):
        cast = _names(m.stars) if getattr(m, "stars", None) else "N/A"

    try:
        box_office = (m.box_office or {}).get("cumulativeWorldwideGross") \
            or (m.box_office or {}).get("grossWorldwide") \
            or m.worldwide_gross or "N/A"
    except (AttributeError, TypeError):
        box_office = "N/A"

    return {
        'title': m.title or "N/A",
        'votes': str(m.votes) if m.votes else "N/A",
        "aka": list_to_str(m.title_akas) if getattr(m, "title_akas", None) else "N/A",
        "seasons": seasons,
        "box_office": box_office,
        'localized_title': m.title_localized or m.title or "N/A",
        'kind': "tv series" if m.is_series() else ("episode" if m.is_episode() else "movie"),
        "imdb_id": m.imdb_id or "N/A",
        "cast": cast,
        "runtime": f"{m.duration} min" if getattr(m, "duration", None) else "N/A",
        "countries": list_to_str(m.countries) if getattr(m, "countries", None) else "N/A",
        "certificates": m.mpaa or m.certificate or "N/A",
        "languages": list_to_str(m.languages_text or m.languages) if (getattr(m, "languages_text", None) or getattr(m, "languages", None)) else "N/A",
        "director": _names(m.directors) if getattr(m, "directors", None) else "N/A",
        "writer": _cat(m, "writer"),
        "producer": _cat(m, "producer"),
        "composer": _cat(m, "composer"),
        "cinematographer": _cat(m, "cinematographer"),
        "music_team": "N/A",
        "distributors": "N/A",
        'release_date': m.release_date or "N/A",
        'year': str(m.year) if m.year else "N/A",
        'genres': list_to_str(m.genres) if getattr(m, "genres", None) else "N/A",
        'poster': _hq_poster(m.cover_url),
        'plot': plot,
        'rating': str(m.rating) if m.rating else "N/A",
        'url': m.url or (f"https://www.imdb.com/title/{m.imdb_id}/" if m.imdb_id else "N/A"),
        'trailers': list(m.trailers) if getattr(m, "trailers", None) else [],
        '_source': 'imdbio',
    }


def _hq_poster(url):
    """OMDb poster URLs point at Amazon's image CDN with a size-limiting suffix
    like '._V1_SX300.jpg'. Stripping that suffix returns the original, full-res image."""
    if not url or url == "N/A":
        return None
    return re.sub(r'\._[A-Z0-9,]+_(?=\.\w+$)', '', url)


async def fetch_poster_bytes(url):
    """Download a poster image ourselves and return raw bytes, or None on failure.
    Telegram's own reply_photo(photo=<url>) sometimes fails (CDN blocks Telegram's
    fetcher, size/dimension limits) even when the URL is perfectly loadable from a
    normal browser/HTTP client — downloading it ourselves and uploading the bytes
    sidesteps that."""
    if not url:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"poster download failed: {e}")
        return None


async def _omdb_search(title, year=None, bulk=False):
    """Search movies/shows via OMDb."""
    if not OMDB_API_KEY:
        logger.warning("OMDB_API_KEY not set, cannot search OMDb")
        return None
    try:
        params = {"apikey": OMDB_API_KEY, "s": title}
        if year:
            params["y"] = year
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://www.omdbapi.com/", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.exception(f"omdb search error: {e}")
        return None

    if data.get("Response") != "True":
        return None
    results = data.get("Search", [])
    if not results:
        return None
    if bulk:
        return [_OmdbFakeMovie(r) for r in results[:10]]
    return await _omdb_get_details(results[0]["imdbID"])


async def _omdb_get_details(imdb_id):
    """Fetch full details via OMDb by IMDb ID."""
    if not OMDB_API_KEY:
        return None
    if isinstance(imdb_id, str) and imdb_id.startswith("omdb_"):
        imdb_id = imdb_id[len("omdb_"):]
    try:
        params = {"apikey": OMDB_API_KEY, "i": imdb_id, "plot": "full" if LONG_IMDB_DESCRIPTION else "short"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://www.omdbapi.com/", params=params)
            resp.raise_for_status()
            m = resp.json()
    except Exception as e:
        logger.exception(f"omdb details error: {e}")
        return None
    if not m or m.get("Response") != "True":
        return None

    plot = m.get("Plot") or "N/A"
    if not LONG_IMDB_DESCRIPTION and plot and len(plot) > 800:
        plot = plot[:800] + "..."

    def _split(field):
        v = m.get(field)
        if not v or v == "N/A":
            return "N/A"
        return list_to_str([p.strip() for p in v.split(",")])

    return {
        'title': m.get("Title", "N/A"),
        'votes': m.get("imdbVotes", "N/A"),
        "aka": "N/A",
        "seasons": m.get("totalSeasons"),
        "box_office": m.get("BoxOffice", "N/A"),
        'localized_title': m.get("Title", "N/A"),
        'kind': "tv series" if m.get("Type") == "series" else "movie",
        "imdb_id": m.get("imdbID", "N/A"),
        "cast": _split("Actors"),
        "runtime": m.get("Runtime", "N/A"),
        "countries": _split("Country"),
        "certificates": m.get("Rated", "N/A"),
        "languages": _split("Language"),
        "director": _split("Director"),
        "writer": _split("Writer"),
        "producer": "N/A",
        "composer": "N/A",
        "cinematographer": "N/A",
        "music_team": "N/A",
        "distributors": "N/A",
        'release_date': m.get("Released", "N/A"),
        'year': m.get("Year", "N/A"),
        'genres': _split("Genre"),
        'poster': _hq_poster(m.get("Poster")),
        'plot': plot,
        'rating': m.get("imdbRating", "N/A"),
        'url': f"https://www.imdb.com/title/{m.get('imdbID')}/" if m.get("imdbID") else "N/A",
        'trailers': [],  # OMDb has no trailer data
        '_source': 'omdb',
    }


async def get_poster(query, bulk=False, id=False, file=None):
    # ── Direct ID lookups ────────────────────────────────────────────────────
    if id:
        result = await _imdbio_get_details(query)
        if result:
            return result
        return await _omdb_get_details(query)

    # ── Parse title + year ───────────────────────────────────────────────────
    query = (query.strip()).lower()
    title = query
    year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
    if year:
        year = list_to_str(year[:1])
        title = (query.replace(year, "")).strip()
    elif file is not None:
        year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
    else:
        year = None

    result = await _imdbio_search(title, year=year, bulk=bulk)
    if result:
        return result
    return await _omdb_search(title, year=year, bulk=bulk)




@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply('🔍 Searching...')
        r, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await k.edit("❌ No results found on OMDb.")
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title') or movie.get('name', 'Unknown')} - {movie.get('year') or (str(movie.get('release_date') or movie.get('first_air_date') or ''))[:4] or 'N/A'}",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await k.edit('🎬 Here is what I found:', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('Give me a movie / series Name')

async def _send_photo_bytes_or_text(message, poster_url, caption, btn):
    """Last resort before giving up on a real photo: download the poster ourselves
    and upload the raw bytes. Only if that also fails do we send plain text — and
    even then with the preview disabled, so we never show Telegram's own low-res
    link-preview card as a stand-in for the poster."""
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
    message = quer_y.message.reply_to_message or quer_y.message
    if not data:
        await quer_y.answer("❌ Could not fetch details.", show_alert=True)
        return

    def _tags(field):
        if not field or field == "N/A":
            return "N/A"
        return " ".join(f"#{p.strip().replace(' ', '_')}" for p in field.split(",") if p.strip())

    # underscore-prefixed so they don't collide with the **locals() spread below
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
        query = data['title'],
        title = data['title'],
        votes = data['votes'],
        aka = data["aka"],
        aka_line = _aka_line,
        seasons = data["seasons"],
        box_office = data['box_office'],
        localized_title = data['localized_title'],
        kind = data['kind'],
        imdb_id = data["imdb_id"],
        cast = data["cast"],
        runtime = data["runtime"],
        countries = data["countries"],
        country_tags = _country_tags,
        certificates = data["certificates"],
        languages = data["languages"],
        language_tags = _language_tags,
        director = data["director"],
        writer = data["writer"],
        producer = data["producer"],
        composer = data["composer"],
        cinematographer = data["cinematographer"],
        music_team = data["music_team"],
        distributors = data["distributors"],
        release_date = data['release_date'],
        year = data['year'],
        genres = data['genres'],
        genre_tags = _genre_tags,
        poster = data['poster'],
        plot = data['plot'],
        rating = data['rating'],
        url = data['url'],
        **locals()
    )
    if data.get('poster'):
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
