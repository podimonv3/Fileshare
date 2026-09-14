import os
from pyrogram import Client, filters
# നിങ്ങളുടെ info ഫയലിൽ നിന്നും ചാനൽ ഐഡി ഇമ്പോർട്ട് ചെയ്യുന്നു
from info import LOG_CHANNEL_ID 

# LOG_CHANNEL_ID ഉള്ള ചാനലിൽ പുതിയ ഫയലുകൾ (Video/Document/Audio) വരുമ്പോൾ മാത്രം ഇത് പ്രവർത്തിക്കും
@Client.on_message(filters.chat(LOG_CHANNEL_ID) & (filters.video | filters.document | filters.audio))
async def auto_channel_caption_editor(client, message):
    file_id = None
    file_name = "File"
    media_type = None

    # 1. വന്ന ഫയലിന്റെ തരവും അതിന്റെ യഥാർത്ഥ പേരും (File Name) കണ്ടെത്തുന്നു
    if message.video:
        media_type = "video"
        file_id = message.video.file_id
        file_name = message.video.file_name or "Video_File"
        
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        file_name = message.document.file_name or "Document_File"
        
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "Audio_File"

    # 2. പഴയ ക്യാപ്ഷൻ പൂർണ്ണമായി ഒഴിവാക്കി ഫയൽ നെയിം മാത്രം കോഡ് രൂപത്തിൽ (`...`) ആക്കുന്നു
    new_caption = f"`{file_name}`"

    try:
        # 3. ചാനലിലെ ആ മെസ്സേജിന്റെ ക്യാപ്ഷൻ നേരിട്ട് എഡിറ്റ് ചെയ്യുന്നു
        await client.edit_message_caption(
            chat_id=message.chat.id,
            message_id=message.id,
            caption=new_caption
        )
        print(f"Successfully updated caption to filename code format for: {file_name}")
        
    except Exception as e:
        print(f"Error while editing channel caption: {e}")

