import os
from pyrogram import Client, filters

# ---------------- SAFE IMPORT SYSTEM ----------------
# info.py ഫയലിൽ നിന്ന് ചാനൽ ഐഡികൾ ക്രാഷ് ആവാതെ സുരക്ഷിതമായി എടുക്കുന്നു
try:
    import info
    SOURCE_CHANNEL_ID = getattr(info, "SOURCE_CHANNEL_ID", None)
    TARGET_CHANNEL_ID = getattr(info, "TARGET_CHANNEL_ID", None)
except ImportError:
    SOURCE_CHANNEL_ID = None
    TARGET_CHANNEL_ID = None

# ചാനൽ ഐഡികൾ കൃത്യമായി നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കാനുള്ള ഫിൽട്ടർ
def is_forwarder_enabled(_, __, message):
    # ഐഡികൾ ഇല്ലെങ്കിലോ അല്ലെങ്കിൽ അവ ശൂന്യമാണെങ്കിലോ ഫംഗ്ഷൻ പ്രവർത്തിക്കില്ല
    if not SOURCE_CHANNEL_ID or not TARGET_CHANNEL_ID:
        return False
    # വന്ന മെസ്സേജ് കൃത്യമായി സോഴ്സ് ചാനലിൽ നിന്നാണോ എന്ന് നോക്കുന്നു
    return message.chat.id == SOURCE_CHANNEL_ID
# -----------------------------------------------------

# ചാനൽ ഐഡികൾ ഉണ്ടെങ്കിൽ മാത്രം പ്രവർത്തിക്കുന്ന ഫിൽട്ടർ സെറ്റ് ചെയ്യുന്നു
dynamic_forward_filter = filters.create(is_forwarder_enabled)

@Client.on_message(dynamic_forward_filter & (filters.video | filters.document | filters.audio))
async def auto_file_forwarder(client, message):
    file_id = None
    file_name = "File"
    media_type = None

    # 1. ഫയൽ തരവും അതിന്റെ യഥാർത്ഥ പേരും കണ്ടെത്തുന്നു
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

    # 2. പഴയ ക്യാപ്ഷൻ മാറ്റി ഫയൽ നെയിം കോഡ് ഫോർമാറ്റിൽ ആക്കുന്നു
    new_caption = f"`{file_name}`"

    try:
        # 3. ടാർഗറ്റ് ചാനലിലേക്ക് ഫയൽ അയക്കുന്നു
        if media_type == "video":
            await client.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=file_id,
                caption=new_caption
            )
        elif media_type == "document":
            await client.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=file_id,
                caption=new_caption
            )
        elif media_type == "audio":
            await client.send_audio(
                chat_id=TARGET_CHANNEL_ID,
                audio=file_id,
                caption=new_caption
            )
        
        print(f"Successfully auto-forwarded clean file to target channel: {file_name}")
        
    except Exception as e:
        # ഒരുവേള പെർമിഷൻ കുറവോ മറ്റോ കാരണം ഫയൽ പോയില്ലെങ്കിലും ബോട്ട് ഓഫ് ആകില്ല
        print(f"Error while auto-forwarding: {e}")

