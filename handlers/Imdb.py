import os
import requests
from io import BytesIO
from PIL import Image, ImageFilter
from pyrogram import Client, filters
from imdb import Cinemagoer # ഫ്രീ IMDb ലൈബ്രറി
from duckduckgo_search import DDGS # ഫ്രീ വെബ് സെർച്ച് ലൈബ്രറി

# IMDb ക്ലയന്റ് ഇനിഷ്യലൈസ് ചെയ്യുന്നു (API Key ആവശ്യമില്ല)
ia = Cinemagoer()

def get_imdb_movie_details(movie_name):
    """ IMDb-യിൽ നിന്ന് സിനിമയുടെ കൃത്യമായ വിവരങ്ങൾ ഫ്രീയായി എടുക്കുന്നു """
    try:
        search_results = ia.search_movie(movie_name)
        if not search_results:
            return None
            
        # ഏറ്റവും അനുയോജ്യമായ ആദ്യത്തെ സിനിമ എടുക്കുന്നു
        movie_obj = search_results[0]
        ia.update(movie_obj) # ഫുൾ ഡാറ്റ അപ്ഡേറ്റ് ചെയ്യുന്നു
        
        title = movie_obj.get('title', movie_name)
        year = movie_obj.get('year', 'N/A')
        rating = movie_obj.get('rating', 'N/A')
        
        # Genres ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു (ഉദാ: #Action #Crime)
        genres_list = [f"#{g.replace(' ', '')}" for g in movie_obj.get('genres', [])]
        genres = " ".join(genres_list) if genres_list else '#N/A'
        
        # പ്രധാന ഭാഷകൾ ഹാഷ്‌ടാഗ് ആക്കുന്നു
        languages_list = [f"#{l.replace(' ', '')}" for l in movie_obj.get('languages', [])]
        language = languages_list[0] if languages_list else '#Unknown'
        
        # IMDb-യിലെ ഔദ്യോഗിക കവർ പോസ്റ്റർ ലിങ്ക്
        imdb_poster = movie_obj.get('full-size cover url') or movie_obj.get('cover url')
        
        return {
            'title': title, 'year': year, 'rating': rating,
            'genres': genres, 'language': language, 'imdb_poster': imdb_poster
        }
    except Exception as e:
        print(f"IMDb Error: {e}")
        return None

def search_free_landscape_image(movie_name):
    """ API Key ഇല്ലാതെ DuckDuckGo വഴി വെബിൽ നിന്ന് ഫ്രീയായി ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു """
    try:
        search_query = f"{movie_name} movie landscape poster wallpaper 16:9"
        with DDGS() as ddgs:
            results = list(ddgs.images(search_query, max_results=2))
            if results:
                return results[0]['image']
    except Exception as e:
        print(f"DuckDuckGo Image Error: {e}")
    return None

def process_smart_blur_landscape(image_url):
    """ ചിത്രം ഡൗൺലോഡ് ചെയ്ത് അത് പോർട്രെയ്റ്റ് ആണെങ്കിൽ വശങ്ങൾ ബ്ലർ ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(image_url, headers=headers, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        # ചിത്രം ഇതിനകം തന്നെ വൈഡ് / ലാൻഡ്‌സ്‌കേപ്പ് ആണെങ്കിൽ എഡിറ്റ് ചെയ്യില്ല
        if orig_w > orig_h * 1.3:
            bio = BytesIO(res.content)
            bio.name = 'landscape.jpg'
            return bio

        # ചിത്രം നീളത്തിലുള്ളതാണെങ്കിൽ (Portrait) ഇരുവശവും ബ്ലർ ചെയ്ത് വൈഡ് ആക്കുന്നു
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
        print(f"Blur Error: {e}")
        return image_url

# /p കമാൻഡ് ഹാൻഡ്‌ലർ
@Client.on_message(filters.command("p") & filters.incoming)
async def free_imdb_movie_search(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ ദയവായി സിനിമയുടെ പേര് നൽകുക. ഉദാ: `/p Maharaja Hostel`")
        return
        
    movie_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔍 IMDb-യിൽ സിനിമ തിരയുന്നു...")
    
    # 1. IMDb വിവരങ്ങൾ ശേഖരിക്കുന്നു
    movie = get_imdb_movie_details(movie_name)
    
    if not movie:
        await status_msg.edit_text("❌ ക്ഷമിക്കണം, IMDb-യിൽ ഈ സിനിമ കണ്ടെത്താനായില്ല.")
        return

    # 2. ചിത്രങ്ങൾക്കായുള്ള തിരച്ചിൽ
    # ആദ്യം DuckDuckGo വഴി നല്ലൊരു ലാൻഡ്‌സ്‌കേപ്പ് ഫോട്ടോ തിരയുന്നു
    await status_msg.edit_text("🖼️ ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രം കണ്ടെത്തുന്നു...")
    final_image_url = search_free_landscape_image(movie_name)
    is_portrait = False
    
    # വെബിൽ ലാൻഡ്‌സ്‌കേപ്പ് ഫോട്ടോ കിട്ടിയില്ലെങ്കിൽ IMDb നൽകിയ ഒറിജിനൽ പോസ്റ്റർ എടുക്കുന്നു
    if not final_image_url:
        final_image_url = movie['imdb_poster']
        is_portrait = True # IMDb നൽകുന്നത് സാധാരണ പോർട്രെയ്റ്റ് ആയിരിക്കും

    if final_image_url:
        # ചിത്രം ഡൗൺലോഡ് ചെയ്ത് ആവശ്യമെങ്കിൽ ബ്ലർ പ്രോസസ്സിംഗ് നടത്തുന്നു
        photo_payload = process_smart_blur_landscape(final_image_url)
        
        # താങ്കൾ ആദ്യം അയച്ചു തന്ന സ്ക്രീൻഷോട്ടിലെ കൃത്യമായ ക്യാപ്ഷൻ ഫോർമാറ്റ്
        caption = (
            f"▶**Film :** __{movie['title']} {movie['year']} | Movie__\n"
            f"▶**Rating :** __{movie['rating']} / 10__\n"
            f"▶**Genre :** __{movie['genres']}__\n"
            f"▶**Lang :** __{movie['language']}__\n\n"
            f"**Team Urvashi Theaters**"
        )
        
        try:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo_payload,
                caption=caption
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ ചിത്രം അയക്കാൻ കഴിഞ്ഞില്ല: {e}")
    else:
        await status_msg.edit_text("❌ സിനിമ വിവരങ്ങൾ ലഭിച്ചു, പക്ഷെ ചിത്രങ്ങൾ ഒന്നും തന്നെ കണ്ടെത്താനായില്ല.")
