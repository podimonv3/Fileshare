import os
import requests
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PIL import Image, ImageFilter

# 🚨 നിങ്ങളുടെ യഥാർത്ഥ TMDb API Key ഇവിടെ നൽകുക 🚨
TMDB_API_KEY = "5f28978232d6d780d64dd0d0e0bbe2f2"

# താങ്കൾ ആവശ്യപ്പെട്ട കൃത്യമായ ക്യാപ്ഷൻ ഫോർമാറ്റ്
IMDB_TEMPLATE = """▶**Film :** __{title} ({year}) | Movie__
▶**Rating :** __{rating} / 10__
▶**Genre :** __{genres}__
▶**Lang :** __{language}__

**Team Urvashi Theaters**"""

def get_tmdb_movie_details(movie_name):
    """ TMDb API വഴി സിനിമയുടെ വിവരങ്ങളും ഒഫീഷ്യൽ ചിത്രങ്ങളും കൃത്യമായി കണ്ടെത്തുന്നു """
    try:
        if not TMDB_API_KEY or TMDB_API_KEY == "5f28978232d6d780d64dd0d0e0bbe2f2":
            return None
            
        # 1. സിനിമ തിരയുന്നു
        search_url = f"https://themoviedb.org/{TMDB_API_KEY}&query={movie_name}"
        search_res = requests.get(search_url, timeout=10).json()
        
        if not search_res.get('results'):
            return None
            
        movie_data = search_res['results'][0] # ആദ്യത്തെ റിസൾട്ട് എടുക്കുന്നു
        movie_id = movie_data['id']
        
        # 2. ഫുൾ ഡീറ്റെയിൽസും ഭാഷയും കണ്ടെത്താൻ സിനിമയുടെ മെയിൻ പേജ് ലോഡ് ചെയ്യുന്നു
        detail_url = f"https://themoviedb.org/{movie_id}?api_key={TMDB_API_KEY}"
        m = requests.get(detail_url, timeout=10).json()
        
        title = m.get('title', movie_name)
        release_date = m.get('release_date', '')
        year = release_date.split('-')[0] if release_date else "N/A"
        rating = str(round(m.get('vote_average', 0), 1))
        
        # ജോണറുകൾ ഹാഷ്‌ടാഗ് ആക്കുന്നു
        genres_list = [f"#{g['name'].replace(' ', '')}" for g in m.get('genres', [])]
        genres = " ".join(genres_list) if genres_list else '#Movie'
        
        # ഭാഷ ഹാഷ്‌ടാഗ് ആക്കുന്നു
        spoken_langs = m.get('spoken_languages', [])
        language = f"#{spoken_langs[0]['english_name'].replace(' ', '')}" if spoken_langs else '#Unknown'
        
        # ലാൻഡ്‌സ്‌കേപ്പ് (Backdrop) നോക്കുന്നു, ഇല്ലെങ്കിൽ പോർട്രെയ്റ്റ് എടുക്കുന്നു
        backdrop = m.get('backdrop_path')
        portrait = m.get('poster_path')
        
        poster_url = None
        is_portrait = False
        
        if backdrop:
            poster_url = f"https://tmdb.org{backdrop}"
        elif portrait:
            poster_url = f"https://tmdb.org{portrait}"
            is_portrait = True
            
        imdb_id = m.get('imdb_id', '')
        url = f"https://imdb.com{imdb_id}/" if imdb_id else "https://imdb.com"
        
        return {
            'title': title, 'year': year, 'rating': rating,
            'genres': genres, 'language': language, 'url': url,
            'poster_url': poster_url, 'is_portrait': is_portrait
        }
    except Exception as e:
        print(f"TMDb Fetch Error: {e}")
    return None

def process_smart_blur_landscape(image_url):
    """ ചിത്രം പോർട്രെയ്റ്റ് ആണെങ്കിൽ വശങ്ങൾ ബ്ലർ ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് (16:9) ആക്കുന്നു """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(image_url, headers=headers, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        if orig_w > orig_h * 1.3:
            bio = BytesIO(res.content)
            bio.name = 'landscape.jpg'
            return bio

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
    except Exception:
        return image_url

# /p കമാൻഡ് ഹാൻഡ്‌ലർ
@Client.on_message(filters.command("p") & filters.incoming)
async def quick_movie_poster(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ ദയവായി സിനിമയുടെ പേര് നൽകുക. ഉദാ: `/p Maharaja Hostel`")
        return
        
    movie_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔍 ഒഫീഷ്യൽ പ്ലാറ്റ്‌ഫോമുകളിൽ ലാൻഡ്‌സ്‌കേപ്പ് ചിത്രങ്ങൾ തിരയുന്നു...")
    
    # TMDb സിസ്റ്റം വഴി വിവരങ്ങളും ചിത്രങ്ങളും എടുക്കുന്നു
    movie = get_tmdb_movie_details(movie_name)
    
    if not movie:
        await status_msg.edit_text("❌ ക്ഷമിക്കണം, ഈ സിനിമയുടെ ഔദ്യോഗിക വിവരങ്ങൾ കണ്ടെത്താനായിില്ല.")
        return

    final_image_url = movie['poster_url']
    # ചിത്രങ്ങൾ ഒന്നും കണ്ടില്ലെങ്കിൽ ഒരു ഡിഫോൾട്ട് ബാക്കപ്പ് ചിത്രം നൽകുന്നു
    if not final_image_url:
        final_image_url = "https://telegra.ph"

    try:
        # ഇമേജ് ലാൻഡ്‌സ്‌കേപ്പ് ഫോർമാറ്റിലേക്ക് മാറ്റുന്നു
        photo_payload = process_smart_blur_landscape(final_image_url)
        
        caption = IMDB_TEMPLATE.format(
            title=movie['title'],
            year=movie['year'],
            rating=movie['rating'],
            genres=movie['genres'],
            language=movie['language']
        )
        
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
