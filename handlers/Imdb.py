import os
import requests
from io import BytesIO
from PIL import Image, ImageFilter
from pyrogram import Client, filters

# നിങ്ങളുടെ TMDb API Key ഇവിടെ നൽകുക
TMDB_API_KEY = "YOUR_TMDB_API_KEY"

def get_movie_details(movie_name):
    try:
        search_url = f"https://themoviedb.org{TMDB_API_KEY}&query={movie_name}"
        response = requests.get(search_url).json()
        
        if not response.get('results'):
            return None
            
        movie_data = response['results'][0]
        movie_id = movie_data['id']
        
        detail_url = f"https://themoviedb.org{movie_id}?api_key={TMDB_API_KEY}"
        detail_response = requests.get(detail_url).json()
        
        title = detail_response.get('title', movie_name)
        release_date = detail_response.get('release_date', '')
        year = release_date.split('-')[0] if release_date else ''
        rating = detail_response.get('vote_average', 'N/A')
        
        # Genres ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു
        genres_list = [f"#{g['name'].replace(' ', '')}" for g in detail_response.get('genres', [])]
        genres = " ".join(genres_list) if genres_list else '#N/A'
        
        # ഭാഷ ഹാഷ്‌ടാഗ് രൂപത്തിലാക്കുന്നു
        spoken_languages = detail_response.get('spoken_languages', [])
        if spoken_languages:
            lang_name = spoken_languages[0]['english_name']
            language = f"#{lang_name.replace(' ', '')}"
        else:
            language = '#Unknown'
            
        # 1. ഒറിജിനൽ ലാൻഡ്‌സ്‌കേപ്പ് (Backdrop) ചിത്രം നോക്കുന്നു
        backdrop_path = detail_response.get('backdrop_path')
        portrait_path = detail_response.get('poster_path')
        
        poster_url = None
        is_portrait = False
        
        if backdrop_path:
            poster_url = f"https://tmdb.org{backdrop_path}"
        elif portrait_path:
            # ലാൻഡ്‌സ്‌കേപ്പ് ഇല്ലെങ്കിൽ പോർട്രെയ്റ്റ് എടുക്കുന്നു (പിന്നീട് എഡിറ്റ് ചെയ്യാൻ)
            poster_url = f"https://tmdb.org{portrait_path}"
            is_portrait = True
            
        return {
            'title': title,
            'year': year,
            'rating': rating,
            'genres': genres,
            'language': language,
            'poster_url': poster_url,
            'is_portrait': is_portrait
        }
    except Exception as e:
        print(f"Error fetching movie data: {e}")
        return None

def convert_portrait_to_landscape(image_url_or_path):
    """
    ഒരു പോർട്രെയ്റ്റ് ചിത്രത്തിന്റെ ഇരുവശങ്ങളിലും ബ്ലർ ചെയ്ത പശ്ചാത്തലം നൽകി
    അതിനെ 16:9 Landscape ഫോർമാറ്റിലേക്ക് മാറ്റുന്ന ഫംഗ്ഷൻ.
    """
    try:
        # ഓൺലൈൻ യുആർഎൽ ആണെങ്കിൽ ഡൗൺലോഡ് ചെയ്യുന്നു
        if image_url_or_path.startswith("http"):
            response = requests.get(image_url_or_path)
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(image_url_or_path)
            
        img = img.convert("RGB")
        orig_w, orig_h = img.size
        
        # 16:9 അനുപാതത്തിലുള്ള പുതിയ ലാൻഡ്‌സ്‌കേപ്പ് അളവ് നിശ്ചയിക്കുന്നു
        target_w = int(orig_h * (16 / 9))
        target_h = orig_h
        
        if target_w < orig_w:
            target_w = orig_w
            target_h = int(orig_w * (9 / 16))
            
        # 1. പശ്ചാത്തലത്തിന് വേണ്ടി ഒറിജിനൽ ചിത്രം വലുതാക്കുന്നു
        bg_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        # പശ്ചാത്തലം നല്ലതുപോലെ ബ്ലർ ചെയ്യുന്നു
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
        
        # 2. ഒറിജിനൽ ചിത്രം നടുവിലായി വെക്കുന്നു
        offset_x = (target_w - orig_w) // 2
        offset_y = (target_h - orig_h) // 2
        bg_img.paste(img, (offset_x, offset_y))
        
        # എഡിറ്റ് ചെയ്ത ചിത്രം ടെലഗ്രാമിന് അയക്കാൻ പാകത്തിൽ ബൈറ്റ്സ് ആക്കി മാറ്റുന്നു
        bio = BytesIO()
        bio.name = 'landscape_poster.jpg'
        bg_img.save(bio, 'JPEG')
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"Image editing failed: {e}")
        return image_url_or_path

# മീഡിയ അയക്കുന്ന പ്രധാന ഫംഗ്ഷൻ
async def send_smart_landscape_media(client, chat_id, file_id, media_type, movie_query_name):
    movie = get_movie_details(movie_query_name)
    
    if movie:
        caption = (
            f"▶**Film :** __{movie['title']} {movie['year']} | Movie__\n"
            f"▶**Rating :** __{movie['rating']} / 10__\n"
            f"▶**Genre :** __{movie['genres']}__\n"
            f"▶**Lang :** __{movie['language']}__\n\n"
            f"**Team Urvashi Theaters**"
        )
        poster = movie['poster_url']
        is_portrait = movie['is_portrait']
    else:
        caption = f"▶**Film :** __{movie_query_name}__\n\n**Team Urvashi Theaters**"
        poster = None
        is_portrait = False

    try:
        # യൂസർ ആവശ്യപ്പെട്ടത് വീഡിയോ ആണെങ്കിൽ നേരിട്ട് വീഡിയോ അയക്കുന്നു
        if media_type == "video":
            await client.send_video(chat_id=chat_id, video=file_id, caption=caption)
            
        # ചിത്രം മാത്രമാണ് ആവശ്യമെങ്കിൽ
        elif media_type == "image" or media_type == "document":
            if poster:
                if is_portrait:
                    # പോർട്രെയ്റ്റ് ചിത്രത്തെ ഇവിടെ വെച്ച് ലാൻഡ്‌സ്‌കേപ്പ് ആയി എഡിറ്റ് ചെയ്യുന്നു
                    edited_photo = convert_portrait_to_landscape(poster)
                    await client.send_photo(chat_id=chat_id, photo=edited_photo, caption=caption)
                else:
                    # റെഡിമെയ്ഡ് ലാൻഡ്‌സ്‌കേപ്പ് ഉണ്ടെങ്കിൽ അത് നേരിട്ട് അയക്കുന്നു
                    await client.send_photo(chat_id=chat_id, photo=poster, caption=caption)
            else:
                # ഇന്റർനെറ്റിൽ ചിത്രം ലഭ്യമല്ലെങ്കിൽ ബോട്ടിന്റെ കൈവശമുള്ള ലോക്കൽ ഫയൽ അയക്കുന്നു
                await client.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
                
    except Exception as e:
        print(f"Failed to send media: {e}")
