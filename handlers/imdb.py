import os
import requests
from io import BytesIO
from PIL import Image, ImageFilter
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from imdb import Cinemagoer
from duckduckgo_search import DDGS

# ഫ്രീ IMDb ലൈബ്രറി ഇനിഷ്യലൈസ് ചെയ്യുന്നു
ia = Cinemagoer()

# താങ്കൾ ആവശ്യപ്പെട്ട /supported ലിസ്റ്റിലുള്ള എല്ലാ ഒഫീഷ്യൽ പ്ലാറ്റ്‌ഫോമുകളും
SUPPORTED_PLATFORMS = [
    "Netflix", "Prime Video", "Amazon Video", "Apple TV+", "Jio Hotstar", "Disney Hotstar", "SonyLIV", "ZEE5",
    "Aha", "Sun NXT", "ETV Win", "JOJO", "Hoichoi", "Chaupal", "Stage", "KableOne", 
    "Waves OTT", "TarangPlus", "Addatimes", "AAO NXT", "ManoramaMAX", "TentKottai", "ShortFlix",
    "Mubi", "Viki", "iQIYI", "WeTV", "VivaMax", "Crunchyroll", "NowTV", "BookMyShow", "YouTube",
    "Eros Now", "Shemaroo", "Ultra Play", "UltraJhakaas", "PlayFlix", "Plex", "Klikk", "SainaPlay",
    "Atrangii", "BongoBD", "Chorki", "Utshob", "Ticketnew", "District", "Airtel Xstream", "TataPlay Binge"
]

def get_imdb_caption_details(movie_name):
    """ IMDb-യിൽ നിന്ന് സിനിമ വിവരങ്ങൾ ക്യാപ്ഷനായി നൽകാൻ ഫ്രീയായി എടുക്കുന്നു """
    try:
        search_results = ia.search_movie(movie_name)
        if not search_results:
            return None
            
        movie_obj = search_results[0] # ഏറ്റവും അനുയോജ്യമായ ആദ്യത്തെ റിസൾട്ട്
        ia.update(movie_obj)
        
        title = movie_obj.get('title', movie_name)
        year = movie_obj.get('year', 'N/A')
        rating = movie_obj.get('rating', 'N/A')
        
        # Genres ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു (ഉദാ: #Action #Thriller)
        genres_list = [f"#{g.replace(' ', '')}" for g in movie_obj.get('genres', [])]
        genres = " ".join(genres_list) if genres_list else '#N/A'
        
        # ഭാഷ ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു (ഉദാ: #Malayalam)
        languages_list = [f"#{l.replace(' ', '')}" for l in movie_obj.get('languages', [])]
        language = " ".join(languages_list) if languages_list else '#Unknown'
        
        imdb_poster = movie_obj.get('full-size cover url') or movie_obj.get('cover url')
        
        return {
            'title': title, 'year': year, 'rating': rating,
            'genres': genres, 'language': language, 'imdb_id': movie_obj.movieID,
            'imdb_poster': imdb_poster
        }
    except Exception as e:
        print(f"IMDb Error: {e}")
        return None

def search_landscape_from_supported_platforms(movie_name):
    """ 
    /supported ലിസ്റ്റിലുള്ള എല്ലാ പ്ലാറ്റ്‌ഫോമുകളിലും ഇന്റർനെറ്റ് വഴി 
    തിരഞ്ഞ് സിനിമയുടെ ഒഫീഷ്യൽ ലാൻഡ്‌സ്‌കേപ്പ് വാൾപേപ്പർ കണ്ടെത്തുന്നു 
    """
    try:
        with DDGS() as ddgs:
            # പ്ലാറ്റ്‌ഫോമുകളെ ടാർഗറ്റ് ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് പോസ്റ്റർ തിരയുന്നു
            search_query = f"{movie_name} movie official landscape poster wallpaper 16:9 widescreen"
            results = list(ddgs.images(search_query, max_results=15)) # കൂടുതൽ കൃത്യതയ്ക്ക് 15 റിസൾട്ട് നോക്കുന്നു
            
            if results:
                for res in results:
                    image_url = res['image']
                    source_url = res.get('url', '').lower()
                    
                    # ചിത്രത്തിന്റെ ഉറവിടം നമ്മുടെ സപ്പോർട്ടഡ് ലിസ്റ്റിൽ ഉള്ളതാണോ എന്ന് നോക്കുന്നു
                    for platform in SUPPORTED_PLATFORMS:
                        clean_platform = platform.lower().replace(" ", "")
                        if clean_platform in source_url:
                            print(f"🎯 Found Landscape from Platform: {platform}")
                            return image_url # പ്ലാറ്റ്‌ഫോമിൽ നിന്നുള്ള ഒറിജിനൽ ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം നൽകുന്നു
                            
                # ലിസ്റ്റിലുള്ള സൈറ്റുകളിൽ നിന്ന് നേരിട്ട് കിട്ടിയില്ലെങ്കിൽ വെബിലെ ആദ്യത്തെ മികച്ച ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം നൽകുന്നു
                return results[0]['image']
    except Exception as e:
        print(f"OTT Multi-Search Error: {e}")
    return None

def process_smart_blur_landscape(image_url):
    """ ചിത്രം ഒരുവേള പോർട്രെയ്റ്റ് ആണെങ്കിൽ ഇരുവശവും ബ്ലർ ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(image_url, headers=headers, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        # ചിത്രം ഇതിനകം തന്നെ ലാൻഡ്‌സ്‌കേപ്പ് (വൈഡ്) ആണെങ്കിൽ എഡിറ്റ് ചെയ്യില്ല
        if orig_w > orig_h * 1.3:
            bio = BytesIO(res.content)
            bio.name = 'landscape.jpg'
            return bio

        # പോർട്രെയ്റ്റ് ആണെങ്കിൽ 16:9 തിയേറ്റർ സ്റ്റൈൽ ലാൻഡ്‌സ്‌കേപ്പ് ആക്കി മാറ്റുന്നു
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
    
    # 1. ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം സപ്പോർട്ടഡ് പ്ലാറ്റ്‌ഫോമുകളിൽ നിന്ന് കണ്ടെത്തുന്നു
    final_image_url = search_landscape_from_supported_platforms(movie_name)
    
    # 2. IMDb വിവരങ്ങൾ ക്യാപ്ഷനായി സെറ്റ് ചെയ്യാൻ എടുക്കുന്നു
    await status_msg.edit_text("📝 IMDb വിവരങ്ങൾ ശേഖരിക്കുന്നു...")
    movie = get_imdb_caption_details(movie_name)
    
    if not movie:
        await status_msg.edit_text("❌ ക്ഷമിക്കണം, ഈ സിനിമയുടെ വിവരങ്ങൾ കണ്ടെത്താനായില്ല.")
        return

    # പ്ലാറ്റ്‌ഫോമുകളിൽ ചിത്രങ്ങൾ ഒന്നും കണ്ടില്ലെങ്കിൽ മാത്രം IMDb ഒറിജിനൽ ബാക്കപ്പ് പോസ്റ്റർ എടുക്കും
    if not final_image_url:
        final_image_url = movie['imdb_poster']

    if final_image_url:
        # ഇമേജ് ലാൻഡ്‌സ്‌കേപ്പ് ലേഔട്ടിലേക്ക് മാറ്റുന്നു
        photo_payload = process_smart_blur_landscape(final_image_url)
        
        # താങ്കൾ ആവശ്യപ്പെട്ട കൃത്യമായ IMDb റിസൾട്ട് ക്യാപ്ഷൻ ഫോർമാറ്റ്
        caption = (
            f"▶**Film :** __{movie['title']} ({movie['year']}) | Movie__\n"
            f"▶**Rating :** __{movie['rating']} / 10__\n"
            f"▶**Genre :** __{movie['genres']}__\n"
            f"▶**Lang :** __{movie['language']}__\n\n"
            f"**Team Urvashi Theaters**"
        )
        
        # നിങ്ങളുടെ ആദ്യ സ്ക്രീൻഷോട്ടിലുള്ള അതേ ഇൻലൈൻ ബട്ടണുകൾ
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Prev", callback_data="prev_page"),
             InlineKeyboardButton("1/5", callback_data="page_num"),
             InlineKeyboardButton("Next ➡️", callback_data="next_page")],
            [InlineKeyboardButton("🔗 Open/Copy URL", url=f"https://imdb.com{movie['imdb_id']}/")],
            [InlineKeyboardButton("❌ Close", callback_data="close_poster")]
        ])
        
        try:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo_payload,
                caption=caption,
                reply_markup=buttons
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ അയക്കാൻ കഴിഞ്ഞില്ല: {e}")
    else:
        await status_msg.edit_text("❌ സിനിമ വിവരങ്ങൾ ലഭിച്ചു, പക്ഷെ ചിത്രങ്ങൾ ഒന്നും കണ്ടെത്താനായില്ല.")

# ക്ലോസ് ബട്ടൺ പ്രവർത്തിക്കാൻ
@Client.on_callback_query(filters.regex("close_poster"))
async def close_callback(client, callback_query):
    await callback_query.message.delete()

