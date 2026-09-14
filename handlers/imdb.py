import os
import requests
import re
from io import BytesIO
from PIL import Image, ImageFilter
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ddgs import DDGS # പുതിയ പതിപ്പിലെ ലൈബ്രറി ഉപയോഗിക്കുന്നു

# താങ്കൾ ആവശ്യപ്പെട്ട /supported ലിസ്റ്റിലുള്ള എല്ലാ ഒഫീഷ്യൽ പ്ലാറ്റ്‌ഫോമുകളും
SUPPORTED_PLATFORMS = [
    "Netflix", "Prime Video", "Amazon Video", "Apple TV+", "Jio Hotstar", "Disney Hotstar", "SonyLIV", "ZEE5",
    "Aha", "Sun NXT", "ETV Win", "JOJO", "Hoichoi", "Chaupal", "Stage", "KableOne", 
    "Waves OTT", "TarangPlus", "Addatimes", "AAO NXT", "ManoramaMAX", "TentKottai", "ShortFlix",
    "Mubi", "Viki", "iQIYI", "WeTV", "VivaMax", "Crunchyroll", "NowTV", "BookMyShow", "YouTube",
    "Eros Now", "Shemaroo", "Ultra Play", "UltraJhakaas", "PlayFlix", "Plex", "Klikk", "SainaPlay",
    "Atrangii", "BongoBD", "Chorki", "Utshob", "Ticketnew", "District", "Airtel Xstream", "TataPlay Binge"
]

def get_free_movie_details(movie_name):
    """ 
    Cinemagoer ഒഴിവാക്കി, ഇന്റർനെറ്റ് വെബ് സ്ക്രാപ്പിംഗ് വഴി 
    സിനിമയുടെ കൃത്യമായ IMDb വിവരങ്ങൾ തത്സമയം എടുക്കുന്ന ഫംഗ്ഷൻ.
    """
    try:
        search_query = f"{movie_name} site:://imdb.com"
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=1))
            if results:
                title_text = results[0]['title'] # ഉദാ: "Maharaja Hostel (2026) - IMDb"
                body_text = results[0]['body']   # വിവരങ്ങൾ അടങ്ങിയ ഭാഗം
                
                # ടൈറ്റിൽ ക്ലീൻ ചെയ്യുന്നു
                clean_title = title_text.split('-')[0].strip()
                
                # വർഷം വേർതിരിക്കുന്നു
                year_match = re.search(r'\((\d{4})\)', clean_title)
                year = year_match.group(1) if year_match else "N/A"
                clean_title = re.sub(r'\(\d{4}\)', '', clean_title).strip()
                
                # റേറ്റിംഗ് ബോഡി ടെക്സ്റ്റിൽ നിന്ന് നോക്കുന്നു
                rating_match = re.search(r'Rating:\s*([\d.]+)/10', body_text, re.IGNORECASE)
                rating = rating_match.group(1) if rating_match else "N/A"
                
                # ജനറുകളും മറ്റ് വിവരങ്ങളും ഒരു ബാക്കപ്പ് ആയി വെക്കുന്നു
                return {
                    'title': clean_title,
                    'year': year,
                    'rating': rating,
                    'genres': '#Movie #Cinema',
                    'language': '#Indian'
                }
    except Exception as e:
        print(f"IMDb Custom Scraping Error: {e}")
        
    # എന്തെങ്കിലും തകരാർ വന്നാൽ ബോട്ട് ക്രാഷ് ആവാതിരിക്കാനുള്ള ബാക്കപ്പ് ഡാറ്റ
    return {
        'title': movie_name.title(),
        'year': "N/A",
        'rating': "N/A",
        'genres': '#Movie',
        'language': '#Unknown'
    }

def search_landscape_from_supported_platforms(movie_name):
    """ /supported ലിസ്റ്റിലുള്ള എല്ലാ പ്ലാറ്റ്‌ഫോമുകളിൽ നിന്നും ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു """
    try:
        search_query = f"{movie_name} movie official landscape poster wallpaper 16:9 widescreen"
        with DDGS() as ddgs:
            results = list(ddgs.images(search_query, max_results=15))
            
            if results:
                for res in results:
                    image_url = res['image']
                    source_url = res.get('url', '').lower()
                    
                    # ചിത്രത്തിന്റെ ലിങ്ക് സപ്പോർട്ടഡ് ലിസ്റ്റിൽ ഉണ്ടോ എന്ന് നോക്കുന്നു
                    for platform in SUPPORTED_PLATFORMS:
                        clean_platform = platform.lower().replace(" ", "")
                        if clean_platform in source_url:
                            print(f"🎯 Found Landscape from Platform: {platform}")
                            return image_url
                            
                # ലിസ്റ്റിലെ സൈറ്റുകളിൽ കണ്ടില്ലെങ്കിൽ വെബിലെ ആദ്യ ലാൻഡ്‌സ്‌കേപ്പ് നൽകുന്നു
                return results[0]['image']
    except Exception as e:
        print(f"Image Web Search Error: {e}")
    return None

def process_smart_blur_landscape(image_url):
    """ ചിത്രം പോർട്രെയ്റ്റ് ആണെങ്കിൽ വശങ്ങൾ ബ്ലർ ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(image_url, headers=headers, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        # ഇതിനകം ലാൻഡ്‌സ്‌കേപ്പ് ആണെങ്കിൽ മാറ്റം വരുത്തില്ല
        if orig_w > orig_h * 1.3:
            bio = BytesIO(res.content)
            bio.name = 'landscape.jpg'
            return bio

        # പോർട്രെയ്റ്റ് ചിത്രത്തിന്റെ വശങ്ങളിൽ ബ്ലർ നൽകുന്നു
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

# /p കമാൻഡ് ഹാൻഡ്‌ലർ
@Client.on_message(filters.command("p") & filters.incoming)
async def quick_movie_poster(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ ദയവായി സിനിമയുടെ പേര് നൽകുക. ഉദാ: `/p Maharaja Hostel`")
        return
        
    movie_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔍 പ്ലാറ്റ്‌ഫോമുകളിൽ ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രങ്ങൾ തിരയുന്നു...")
    
    # 1. സപ്പോർട്ടഡ് പ്ലാറ്റ്‌ഫോമുകളിൽ നിന്ന് ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു
    final_image_url = search_landscape_from_supported_platforms(movie_name)
    
    # 2. ക്രാഷ് ഫ്രീ സിസ്റ്റം വഴി വെബിൽ നിന്ന് IMDb വിവരങ്ങൾ എടുക്കുന്നു
    await status_msg.edit_text("📝 IMDb വിവരങ്ങൾ ശേഖരിക്കുന്നു...")
    movie = get_free_movie_details(movie_name)

    # ചിത്രങ്ങൾ ഒന്നും കണ്ടില്ലെങ്കിൽ ഒരു ഡിഫോൾട്ട് ബാക്കപ്പ് ചിത്രം നൽകാം
    if not final_image_url:
        final_image_url = "https://telegra.ph"

    try:
        # ഇമേജ് ലാൻഡ്‌സ്‌കേപ്പ് ഫോർമാറ്റിലേക്ക് മാറ്റുന്നു
        photo_payload = process_smart_blur_landscape(final_image_url)
        
        # താങ്കൾ ആവശ്യപ്പെട്ട കൃത്യമായ ക്യാപ്ഷൻ
        caption = (
            f"▶**Film :** __{movie['title']} ({movie['year']}) | Movie__\n"
            f"▶**Rating :** __{movie['rating']} / 10__\n"
            f"▶**Genre :** __{movie['genres']}__\n"
            f"▶**Lang :** __{movie['language']}__\n\n"
            f"**Team Urvashi Theaters**"
        )
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Prev", callback_data="prev_page"),
             InlineKeyboardButton("1/5", callback_data="page_num"),
             InlineKeyboardButton("Next ➡️", callback_data="next_page")],
            [InlineKeyboardButton("🔗 Open/Copy URL", url="https://imdb.com")],
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
