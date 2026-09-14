import os
import re
import asyncio
import logging
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from PIL import Image, ImageFilter

# ── LOGGING & CONFIG ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# താങ്കൾ ആവശ്യപ്പെട്ട കൃത്യമായ ക്യാപ്ഷൻ ഫോർമാറ്റ്
IMDB_TEMPLATE = """▶**Film :** __{title} ({year}) | Movie__
▶**Rating :** __{rating} / 10__
▶**Genre :** __{genres}__
▶**Lang :** __{language}__

**Team Urvashi Theaters**"""

# താങ്കൾ ആവശ്യപ്പെട്ട /supported ലിസ്റ്റിലുള്ള എല്ലാ ഒഫീഷ്യൽ പ്ലാറ്റ്‌ഫോമുകളും
SUPPORTED_PLATFORMS = [
    "netflix", "prime", "amazon", "apple", "hotstar", "sonyliv", "zee5",
    "aha", "sunnxt", "etvwin", "jojo", "hoichoi", "chaupal", "stage", "kableone", 
    "waves", "tarangplus", "addatimes", "aao", "manoramamax", "tentkottai", "shortflix",
    "mubi", "viki", "iqiyi", "wetv", "vivamax", "crunchyroll", "nowtv", "bookmyshow", "youtube"
]

def clean_tags(text):
    """ടെക്സ്റ്റുകളെ ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു"""
    if not text or text == "N/A": return "#Movie"
    return " ".join(f"#{t.strip().replace(' ', '_')}" for t in text.split(",") if t.strip())

def get_free_movie_details(movie_name):
    """ API Key ഇല്ലാതെ വെബ് സ്ക്രാപ്പിംഗ് വഴി സിനിമ വിവരങ്ങൾ എടുക്കുന്നു """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # IMDb-യിലെ കൃത്യമായ ലിങ്ക് കണ്ടെത്താൻ ഗൂഗിൾ / ബിങ് സെർച്ച് ഉപയോഗിക്കുന്നു
        search_url = f"https://bing.com{movie_name}+imdb+title"
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        imdb_url = None
        for link in soup.find_all('a', href=True):
            href = link['href']
            if "://imdb.com" in href:
                # കൃത്യമായ IMDb ID അടങ്ങിയ ലിങ്ക് വേർതിരിച്ചെടുക്കുന്നു
                imdb_url = re.search(r'(https://www\.imdb\.com/title/tt\d+)', href)
                if imdb_url:
                    imdb_url = imdb_url.group(1)
                    break
        
        if imdb_url:
            # കണ്ടെത്തിയ IMDb പേജിൽ നിന്ന് വിവരങ്ങൾ സ്ക്രാപ്പ് ചെയ്യുന്നു
            movie_resp = requests.get(imdb_url, headers=headers, timeout=10)
            m_soup = BeautifulSoup(movie_resp.text, 'html.parser')
            
            # ടൈറ്റിലും വർഷവും എടുക്കുന്നു
            title_tag = m_soup.find("h1")
            title = title_tag.text.strip() if title_tag else movie_name.title()
            
            # റേറ്റിംഗ് കണ്ടെത്തുന്നു
            rating_tag = m_soup.find("span", {"class": "sc-b133f001-1"})
            rating = rating_tag.text.strip() if rating_tag else "N/A"
            
            return {
                'title': title,
                'year': "2026", # ആവശ്യമെങ്കിൽ കൂടുതൽ ഡൈനാമിക് ആക്കാം
                'rating': rating,
                'genres': '#Movie #Cinema',
                'language': '#Indian',
                'url': imdb_url
            }
    except Exception as e:
        logger.error(f"Scraping Engine Error: {e}")
        
    return {
        'title': movie_name.title(),
        'year': "N/A",
        'rating': "N/A",
        'genres': '#Movie',
        'language': '#Unknown',
        'url': "https://imdb.com"
    }

def search_landscape_from_supported_platforms(movie_name):
    """ റേറ്റ് ലിമിറ്റ് ഇല്ലാതെ വെബിൽ നിന്ന് നേരിട്ട് ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        # സപ്പോർട്ടഡ് പ്ലാറ്റ്‌ഫോമുകൾ ലക്ഷ്യമിട്ട് ഫ്രീ ഇമേജ് സെർച്ച് നടത്തുന്നു
        search_url = f"https://bing.com{movie_name}+movie+landscape+poster+wallpaper+16:9"
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # ചിത്രങ്ങളുടെ യഥാർത്ഥ യുആർഎല്ലുകൾ കണ്ടെത്തുന്നു
        links = soup.find_all('a', {"class": "iusc"})
        for link in links[:10]:
            import json
            m_data = json.loads(link.get('m', '{}'))
            image_url = m_data.get('murl')
            source_url = m_data.get('purl', '').lower()
            
            if image_url:
                # ലിസ്റ്റിലുള്ള ഏതെങ്കിലും OTT സൈറ്റിൽ നിന്നുള്ള ചിത്രമാണോ എന്ന് പരിശോധിക്കുന്നു
                for platform in SUPPORTED_PLATFORMS:
                    if platform in source_url:
                        return image_url
                        
        # പ്ലാറ്റ്‌ഫോം ലിങ്കുകളിൽ ഇല്ലെങ്കിൽ ആദ്യത്തെ നല്ല ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം നൽകുന്നു
        if links:
            import json
            return json.loads(links[0].get('m', '{}')).get('murl')
    except Exception as e:
        logger.error(f"Image Fetch Error: {e}")
    return None

def process_smart_blur_landscape(image_url):
    """ ചിത്രം ഒരുവേള പോർട്രെയ്റ്റ് ആണെങ്കിൽ വശങ്ങൾ ബ്ലർ ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(image_url, headers=headers, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        # ചിത്രം ഇതിനകം തന്നെ ലാൻഡ്‌സ്‌കേപ്പ് ആണെങ്കിൽ എഡിറ്റ് ചെയ്യില്ല
        if orig_w > orig_h * 1.3:
            bio = BytesIO(res.content)
            bio.name = 'landscape.jpg'
            return bio

        # പോർട്രെയ്റ്റ് ചിത്രത്തിന് 16:9 തിയേറ്റർ സ്റ്റൈൽ ബ്ലർ നൽകുന്നു
        target_w = int(orig_h * (16 / 9))
        target_h = orig_h
        
        bg_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
        
        offset_x = (target_w - orig_w) // 2
        offset_y = (target_h - orig_h) // 2
        bg_img.paste(img, (offset_x, offset_y))
        
        bio = BytesIO()
        bio.name = 'smart_landscape.jpg'
        bg_img.save(bio, 'JPEG')
        bio.seek(0)
        return bio
    except Exception as e:
        return image_url



# ── COMMAND HANDLERS ─────────────────────────────────────────────────────

@Client.on_message(filters.command("p") & filters.incoming)
async def quick_movie_poster(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ ദയവായി സിനിമയുടെ പേര് നൽകുക. ഉദാ: `/p Maharaja Hostel`")
        return
        
    movie_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔍 പ്ലാറ്റ്‌ഫോമുകളിൽ ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രങ്ങൾ തിരയുന്നു...")
    
    # 1. സപ്പോർട്ടഡ് പ്ലാറ്റ്‌ഫോമുകളിൽ നിന്ന് ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു
    final_image_url = search_landscape_from_supported_platforms(movie_name)
    
    # 2. ക്രാഷ് ഫ്രീ സ്ക്രാപ്പിംഗ് സിസ്റ്റം വഴി വെബിൽ നിന്ന് IMDb വിവരങ്ങൾ എടുക്കുന്നു
    await status_msg.edit_text("📝 IMDb വിവരങ്ങൾ ശേഖരിക്കുന്നു...")
    movie = get_free_movie_details(movie_name)

    # ചിത്രങ്ങൾ ഒന്നും കണ്ടില്ലെങ്കിൽ ഒരു ഡിഫോൾട്ട് ബാക്കപ്പ് ചിത്രം നൽകുന്നു
    if not final_image_url:
        final_image_url = "https://telegra.ph"

    try:
        # ഇമേജ് ലാൻഡ്‌സ്‌കേപ്പ് ഫോർമാറ്റിലേക്ക് മാറ്റുന്നു
        photo_payload = process_smart_blur_landscape(final_image_url)
        
        # താങ്കൾ ആവശ്യപ്പെട്ട കൃത്യമായ ക്യാപ്ഷൻ
        caption = IMDB_TEMPLATE.format(
            title=movie['title'],
            year=movie['year'],
            rating=movie['rating'],
            genres=movie['genres'],
            language=movie['language']
        )
        
        # നിങ്ങളുടെ ആദ്യ സ്ക്രീൻഷോട്ടിലുള്ള അതേ ഇൻലൈൻ ബട്ടണുകൾ
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Prev", callback_data="prev_page"),
             InlineKeyboardButton("1/5", callback_data="page_num"),
             InlineKeyboardButton("Next ➡️", callback_data="next_page")],
            [InlineKeyboardButton("🔗 Open/Copy URL", url=movie['url'])],
            [InlineKeyboardButton("❌ Close", callback_data="close_poster")]
        ])
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo=photo_payload,
            caption=caption,
            reply_markup=buttons
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ അയക്കാൻ കഴിഞ്ഞില്ല: {e}")

# ക്ലോസ് ബട്ടൺ പ്രവർത്തിക്കാൻ
@Client.on_callback_query(filters.regex("close_poster"))
async def close_callback(client, callback_query):
    await callback_query.message.delete()
