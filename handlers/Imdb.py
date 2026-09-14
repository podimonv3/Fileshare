import os
import requests
from io import BytesIO
from PIL import Image, ImageFilter
from pyrogram import Client, filters

# നിങ്ങളുടെ TMDb API Key ഇവിടെ നൽകുക
TMDB_API_KEY = "5f28978232d6d780d64dd0d0e0bbe2f2"

def get_movie_details(movie_name):
    """ TMDb-യിൽ നിന്ന് സിനിമയുടെ വിവരങ്ങളും ചിത്രങ്ങളും എടുക്കുന്നു """
    try:
        search_url = f"https://themoviedb.org{TMDB_API_KEY}&query={movie_name}"
        response = requests.get(search_url).json()
        
        if not response.get('results'):
            return None
            
        movie_data = response['results'][0] # ആദ്യത്തെ റിസൾട്ട് എടുക്കുന്നു
        movie_id = movie_data['id']
        
        detail_url = f"https://themoviedb.org{movie_id}?api_key={TMDB_API_KEY}"
        detail_response = requests.get(detail_url).json()
        
        title = detail_response.get('title', movie_name)
        release_date = detail_response.get('release_date', '')
        year = release_date.split('-')[0] if release_date else 'N/A'
        rating = detail_response.get('vote_average', 'N/A')
        
        backdrop_path = detail_response.get('backdrop_path')
        portrait_path = detail_response.get('poster_path')
        
        poster_url = None
        is_portrait = False
        
        # ലാൻഡ്‌സ്‌കേപ്പ് (Backdrop) നോക്കുന്നു, ഇല്ലെങ്കിൽ പോർട്രെയ്റ്റ് എടുക്കുന്നു
        if backdrop_path:
            poster_url = f"https://tmdb.org{backdrop_path}"
        elif portrait_path:
            poster_url = f"https://tmdb.org{portrait_path}"
            is_portrait = True
            
        return {
            'title': title, 'year': year, 'rating': rating,
            'poster_url': poster_url, 'is_portrait': is_portrait
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

def convert_portrait_to_landscape(image_url):
    """ പോർട്രെയ്റ്റ് ചിത്രത്തെ ബ്ലർ പശ്ചാത്തലമുള്ള ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു """
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        orig_w, orig_h = img.size
        
        target_w = int(orig_h * (16 / 9))
        target_h = orig_h
        
        bg_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
        
        offset_x = (target_w - orig_w) // 2
        offset_y = (target_h - orig_h) // 2
        bg_img.paste(img, (offset_x, offset_y))
        
        bio = BytesIO()
        bio.name = 'landscape.jpg'
        bg_img.save(bio, 'JPEG')
        bio.seek(0)
        return bio
    except Exception as e:
        return image_url

# /p ಕಮಾಂಡ್ ഹാൻഡ്‌ലർ
@Client.on_message(filters.command("p") & filters.incoming)
async def quick_movie_poster(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ ദയവായി സിനിമയുടെ പേര് നൽകുക. ഉദാ: `/p Maharaja Hostel`")
        return
        
    movie_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔍 തിരയുന്നു...")
    
    movie = get_movie_details(movie_name)
    
    if not movie or not movie['poster_url']:
        await status_msg.edit_text("❌ സിനിമയോ ചിത്രങ്ങളോ കണ്ടെത്താനായില്ല.")
        return
        
    # നിങ്ങളുടെ ആദ്യത്തെ സ്ക്രീൻഷോട്ടിലെ അതേ ക്യാപ്ഷൻ ഫോർമാറ്റ്
    caption = (
        f"🎬 **{movie['title']}**\n\n"
        f"📅 **Year :** {movie['year']}\n"
        f"⭐ **IMDb Rating :** {movie['rating']}/10\n"
        f"📁 **Type :** Landscape\n\n"
        f"⚡ *Powered by @Poster_Verse*"
    )
    
    # പോർട്രെയ്റ്റ് ആണെങ്കിൽ എഡിറ്റ് ചെയ്ത് ലാൻഡ്‌സ്‌കേപ്പ് ആക്കുന്നു
    if movie['is_portrait']:
        final_photo = convert_portrait_to_landscape(movie['poster_url'])
    else:
        final_photo = movie['poster_url']
        
    try:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=final_photo,
            caption=caption
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ അയക്കാൻ സാധിച്ചില്ല: {e}")
