import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from info import OWNER_ID
from database import get_group_locks, set_group_lock

# 🔒 ബോട്ടിൽ സപ്പോർട്ട് ചെയ്യുന്ന മുഴുവൻ ലോക്ക് ലിസ്റ്റുകൾ
VALID_LOCKS = {
    "photos": "Photos",
    "videos": "Videos",
    "stickers": "Stickers / Big Emojis",
    "voice": "Voice Messages",
    "audio": "Audios / Music",
    "document": "Documents / Files",
    "animation": "GIFs / Gifs Games",
    "poll": "Polls & Quizzes",
    "video_note": "Video Messages (Teleposts)",
    "contact": "Contacts Share",
    "location": "Locations Share",
    "inline": "Inline Bot Messages",
    "story": "Telegram Stories",
    "game": "Telegram Games",
    "channel": "Messages sent as a Channel"
}

# 🛠️ 1. ലോക്ക് ചെയ്യാനും അൺലോക്ക് ചെയ്യാനുമുള്ള അഡ്മിൻ കമാൻഡുകൾ
@Client.on_message(filters.command(["lock", "unlock"]) & filters.group)
async def lock_unlock_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    
    if not user_id:
        return

    # അഡ്മിൻ പദവി പരിശോധിക്കുന്നു
    try:
        member = await chat.get_member(user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
            return
    except:
        return

    if len(message.command) < 2:
        available_types = "\n".join([f"• <code>{k}</code> ({v})" for k, v in VALID_LOCKS.items()])
        await message.reply_text(
            f"⚠️ **ഉപയോഗിക്കേണ്ട രീതി:**\n"
            f"🔒 ലോക്ക് ചെയ്യാൻ: <code>/lock [media_type]</code>\n"
            f"🔓 അൺലോക്ക് ചെയ്യാൻ: <code>/unlock [media_type]</code>\n\n"
            f"**സപ്പോർട്ട് ചെയ്യുന്ന Media Types:**\n{available_types}",
            parse_mode=enums.ParseMode.HTML
        )
        return

    action = message.command[0].lower() # lock അല്ലെങ്കിൽ unlock
    media = message.command[1].lower()

    if media not in VALID_LOCKS:
        await message.reply_text(f"❌ തെറ്റായ മീഡിയ ടൈപ്പ്! പരിശോധിക്കാൻ വെറുതെ <code>/{action}</code> എന്ന് ടൈപ്പ് ചെയ്യുക.")
        return

    status = True if action == "lock" else False
    set_group_lock(chat_id, media, status)
    
    status_text = "🔒 **ലോക്ക് ചെയ്തു (Delete Mode)**" if status else "🔓 **അനുവദിച്ചു (Allow Mode)**"
    await message.reply_text(f"✅ ഈ ഗ്രൂപ്പിൽ <b>{VALID_LOCKS[media].upper()}</b> ഇനി മുതൽ {status_text}!", parse_mode=enums.ParseMode.HTML)


# 🛡️ 2. ഗ്രൂപ്പിൽ വരുന്ന മെസ്സേജുകൾ പരിശോധിച്ച് ലോക്ക് ചെയ്തവ ഡിലീറ്റ് ചെയ്യുന്ന മെയിൻ സിസ്റ്റം
@Client.on_message(filters.group, group=2)
async def check_group_media_locks(client: Client, message: Message):
    chat_id = message.chat.id

    # ചാനൽ അക്കൗണ്ടുകൾ വഴിയാണ് മെസ്സേജ് വരുന്നതെങ്കിൽ (Linked channel അല്ലാത്തവ)
    locks = get_group_locks(chat_id)
    if message.sender_chat and message.sender_chat.type == enums.ChatType.CHANNEL:
        if locks.get("channel") and not message.is_automatic_forward:
            try:
                await message.delete()
                return
            except:
                pass

    if not message.from_user:
        return
        
    user_id = message.from_user.id

    # അഡ്മിൻമാർ അയക്കുന്ന മീഡിയകൾ ബോട്ട് ഡിലീറ്റ് ചെയ്യില്ല
    try:
        member = await chat.get_member(user_id)
        if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID:
            return
    except:
        return

    should_delete = False
    media_name = ""

    # 🔍 നിങ്ങളുടെ സ്ക്രീൻഷോട്ടിൽ ഉള്ള എല്ലാ ഫീച്ചറുകളും ഇവിടെ വേർതിരിച്ച് ചെക്ക് ചെയ്യുന്നു:
    if message.photo and locks.get("photos"):
        should_delete = True
        media_name = VALID_LOCKS["photos"]
    elif message.video and locks.get("videos"):
        should_delete = True
        media_name = VALID_LOCKS["videos"]
    elif message.sticker and locks.get("stickers"):
        should_delete = True
        media_name = VALID_LOCKS["stickers"]
    elif message.voice and locks.get("voice"):
        should_delete = True
        media_name = VALID_LOCKS["voice"]
    elif message.audio and locks.get("audio"):
        should_delete = True
        media_name = VALID_LOCKS["audio"]
    elif message.document and locks.get("document"):
        should_delete = True
        media_name = VALID_LOCKS["document"]
    elif message.animation and locks.get("animation"):
        should_delete = True
        media_name = VALID_LOCKS["animation"]
    elif message.poll and locks.get("poll"):
        should_delete = True
        media_name = VALID_LOCKS["poll"]
    elif message.video_note and locks.get("video_note"):
        should_delete = True
        media_name = VALID_LOCKS["video_note"]
    elif message.contact and locks.get("contact"):
        should_delete = True
        media_name = VALID_LOCKS["contact"]
    elif message.location and locks.get("location"):
        should_delete = True
        media_name = VALID_LOCKS["location"]
    elif message.via_bot and locks.get("inline"):
        should_delete = True
        media_name = VALID_LOCKS["inline"]
    elif message.story and locks.get("story"):
        should_delete = True
        media_name = VALID_LOCKS["story"]
    elif message.game and locks.get("game"):
        should_delete = True
        media_name = VALID_LOCKS["game"]

    # 🚫 ലോക്ക് ചെയ്ത ഉള്ളടക്കം കണ്ടെത്തിയാൽ തൽക്ഷണം ഡിലീറ്റ് ചെയ്യും
    if should_delete:
        try:
            await message.delete()
            warn = await client.send_message(
                chat_id=chat_id,
                text=f"⚠️ {message.from_user.mention}, ഈ ഗ്രൂപ്പിൽ <b>{media_name}</b> അയക്കാൻ അനുവാദമില്ല! അത് ഡിലീറ്റ് ചെയ്തിട്ടുണ്ട്.",
                parse_mode=enums.ParseMode.HTML
            )
            # ഗ്രൂപ്പ് ചാറ്റ് ബോക്സ് എപ്പോഴും ക്ലീൻ ആയിരിക്കാൻ അലേർട്ട് 5 സെക്കൻഡിനുള്ളിൽ ഡിലീറ്റ് ആകും ⏱️
            await asyncio.sleep(5)
            await warn.delete()
        except:
            pass
