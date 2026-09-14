import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from info import OWNER_ID
from database import get_group_locks, set_group_lock

# 🔒 മീഡിയകളും, സിസ്റ്റം സർവീസുകളും, ടെക്സ്റ്റ് എൻ്റിറ്റികളും അടങ്ങിയ ലിസ്റ്റ്
VALID_LOCKS = {
    "photos": "Photos", "videos": "Videos", "stickers": "Stickers / Emojis",
    "voice": "Voice Messages", "audio": "Audios / Music", "document": "Documents",
    "animation": "GIFs / Animations", "poll": "Polls", "video_note": "Video Messages",
    "contact": "Contacts", "location": "Locations", "inline": "Inline Bots",
    "story": "Stories", "game": "Games", "channel": "As a Channel",
    "new_members": "New Members Info", "left_members": "Left Members Info",
    "title_changed": "Group Title Changed", "photo_changed": "Group Photo Updates",
    "pinned": "Pinned Messages Info", "video_chat": "Video Chat Actions",
    "fwd_channel": "Channel Forwards", "usernames": "@Usernames",
    "hashtags": "#Hashtags", "commands": "/Commands", "emails": "E-mails",
    "links": "Links / URLs", "text_styles": "Bold/Italic/Spoiler", "edited": "Edited Messages"
}

# 🎛️ ബട്ടണുകൾ നിർമ്മിക്കുന്ന ഫങ്ക്ഷൻ
def get_locks_markup(chat_id: int):
    locks = get_group_locks(chat_id)
    keyboard = []
    row = []
    for key, name in VALID_LOCKS.items():
        status_emoji = "🗑️" if locks.get(key) else "✅"
        row.append(InlineKeyboardButton(f"{name} {status_emoji}", callback_data=f"lck_{key}_{chat_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📊 Close Settings", callback_data=f"lck_close_{chat_id}")])
    return InlineKeyboardMarkup(keyboard)


# 1️⃣ /settings കമാൻഡ്
@Client.on_message(filters.command("settings") & filters.group)
async def group_settings_panel(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id: return
    try:
        member = await message.chat.get_member(user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
            return
    except: return

    await message.reply_text(
        f"⚙️ <b>★ {message.chat.title} - SETTINGS ★</b>\n\n"
        f"ഗ്രൂപ്പ് കൺട്രോൾ പാനൽ വഴി മാറ്റങ്ങൾ വരുത്താം:\n"
        f"✅ = <b>Allow (അനുവദിച്ചു)</b>\n"
        f"🗑️ = <b>Delete (ലോക്ക് ചെയ്തു)</b>",
        reply_markup=get_locks_markup(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )


# 2️⃣ ബട്ടൺ ആക്ഷനുകൾ
@Client.on_callback_query(filters.regex("^lck_"))
async def locks_callback_handler(client: Client, query):
    data_split = query.data.split("_")
    action = data_split[1]
    try: chat_id = int(data_split[2])
    except: return

    try:
        member = await client.get_chat_member(chat_id, query.from_user.id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and query.from_user.id != OWNER_ID:
            await query.answer("🔒 അഡ്മിൻമാർക്ക് മാത്രമേ അനുവാദമുള്ളൂ!", show_alert=True)
            return
    except: return

    if action == "close":
        await query.message.delete()
        return

    locks = get_group_locks(chat_id)
    new_status = not locks.get(action, False)
    set_group_lock(chat_id, action, new_status)
    
    alert_text = f"{VALID_LOCKS[action]} ലോക്ക് ചെയ്തു!" if new_status else f"{VALID_LOCKS[action]} അനുവദിച്ചു!"
    await query.answer(alert_text)
    try: await query.edit_message_reply_markup(reply_markup=get_locks_markup(chat_id))
    except: pass


# 3️⃣ മെസ്സേജ് ചെക്കിങ് സിസ്റ്റം (ഏറ്റവും സുരക്ഷിതമാക്കിയത് 🛡️)
@Client.on_message(filters.group, group=2)
async def check_group_media_locks(client: Client, message: Message):
    chat_id = message.chat.id
    locks = get_group_locks(chat_id)

    # 1. ചാനൽ പേരിൽ വരുന്ന മെസ്സേജുകൾ തടയാൻ
    if getattr(message, "sender_chat", None) and message.sender_chat.type == enums.ChatType.CHANNEL:
        if locks.get("channel") and not getattr(message, "is_automatic_forward", False):
            try: await message.delete(); return
            except: pass

    should_delete = False
    media_name = ""

    # 2. ചാനലുകളിൽ നിന്നുള്ള ഫോർവേഡുകൾ ലോക്ക് ചെയ്തിട്ടുണ്ടെങ്കിൽ
    if getattr(message, "forward_from_chat", None) and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        if locks.get("fwd_channel"):
            should_delete = True

    # 3. സിസ്റ്റം സർവീസ് മെസ്സേജുകൾ ചെക്കിങ് (🚨 getattr ഉപയോഗിച്ച് സുരക്ഷിതമാക്കി 🚨)
    if getattr(message, "new_chat_members", None) and locks.get("new_members"): should_delete = True
    elif getattr(message, "left_chat_member", None) and locks.get("left_members"): should_delete = True
    elif getattr(message, "new_chat_title", None) and locks.get("title_changed"): should_delete = True
    elif (getattr(message, "new_chat_photo", None) or getattr(message, "delete_chat_photo", None)) and locks.get("photo_changed"): should_delete = True
    elif getattr(message, "pinned_message", None) and locks.get("pinned"): should_delete = True
    elif (getattr(message, "video_chat_started", None) or getattr(message, "video_chat_ended", None) or getattr(message, "video_chat_members_invited", None) or getattr(message, "video_chat_scheduled", None)) and locks.get("video_chat"): should_delete = True

    # 4. സാധാരണ മെമ്പർമാരുടെ മെസ്സേജുകൾ പരിശോധിക്കുന്നു
    elif getattr(message, "from_user", None):
        user_id = message.from_user.id
        try:
            member = await message.chat.get_member(user_id)
            if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID:
                return
        except: return

        # മീഡിയ ടൈപ്പുകൾ ചെക്കിങ് (🚨 getattr സുരക്ഷാ ലോക്ക് 🚨)
        if getattr(message, "photo", None) and locks.get("photos"): should_delete = True; media_name = VALID_LOCKS["photos"]
        elif getattr(message, "video", None) and locks.get("videos"): should_delete = True; media_name = VALID_LOCKS["videos"]
        elif getattr(message, "sticker", None) and locks.get("stickers"): should_delete = True; media_name = VALID_LOCKS["stickers"]
        elif getattr(message, "voice", None) and locks.get("voice"): should_delete = True; media_name = VALID_LOCKS["voice"]
        elif getattr(message, "audio", None) and locks.get("audio"): should_delete = True; media_name = VALID_LOCKS["audio"]
        elif getattr(message, "document", None) and locks.get("document"): should_delete = True; media_name = VALID_LOCKS["document"]
        elif getattr(message, "animation", None) and locks.get("animation"): should_delete = True; media_name = VALID_LOCKS["animation"]
        elif getattr(message, "poll", None) and locks.get("poll"): should_delete = True; media_name = VALID_LOCKS["poll"]
        elif getattr(message, "video_note", None) and locks.get("video_note"): should_delete = True; media_name = VALID_LOCKS["video_note"]
        elif getattr(message, "contact", None) and locks.get("contact"): should_delete = True; media_name = VALID_LOCKS["contact"]
        elif getattr(message, "location", None) and locks.get("location"): should_delete = True; media_name = VALID_LOCKS["location"]
        elif getattr(message, "via_bot", None) and locks.get("inline"): should_delete = True; media_name = VALID_LOCKS["inline"]
        elif getattr(message, "story", None) and locks.get("story"): should_delete = True; media_name = VALID_LOCKS["story"]
        elif getattr(message, "game", None) and locks.get("game"): should_delete = True; media_name = VALID_LOCKS["game"]

        # ടെക്സ്റ്റ് എൻ്റിറ്റികൾ ചെക്കിങ്
        elif (getattr(message, "text", None) or getattr(message, "caption", None)):
            entities = message.entities or message.caption_entities
            if entities:
                for ent in entities:
                    if ent.type == enums.MessageEntityType.MENTION and locks.get("usernames"):
                        should_delete = True; media_name = VALID_LOCKS["usernames"]
                    elif ent.type == enums.MessageEntityType.HASHTAG and locks.get("hashtags"):
                        should_delete = True; media_name = VALID_LOCKS["hashtags"]
                    elif ent.type == enums.MessageEntityType.BOT_COMMAND and locks.get("commands"):
                        should_delete = True; media_name = VALID_LOCKS["commands"]
                    elif ent.type == enums.MessageEntityType.EMAIL and locks.get("emails"):
                        should_delete = True; media_name = VALID_LOCKS["emails"]
                    elif ent.type in [enums.MessageEntityType.URL, enums.MessageEntityType.TEXT_LINK] and locks.get("links"):
                        should_delete = True; media_name = VALID_LOCKS["links"]
                    elif ent.type in [enums.MessageEntityType.BOLD, enums.MessageEntityType.ITALIC, enums.MessageEntityType.SPOILER, enums.MessageEntityType.CODE] and locks.get("text_styles"):
                        should_delete = True; media_name = VALID_LOCKS["text_styles"]

    # 🚫 ലോക്ക് ചെയ്തതാണെങ്കിൽ തൽക്ഷണം ഡിലീറ്റ് ചെയ്യും
    if should_delete:
        try:
            await message.delete()
            if media_name:
                warn = await client.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {message.from_user.mention}, ഈ ഗ്രൂപ്പിൽ <b>{media_name}</b> ഉപയോഗിക്കാൻ അനുവാദമില്ല! അത് ഡിലീറ്റ് ചെയ്തിട്ടുണ്ട്.",
                    parse_mode=enums.ParseMode.HTML
                )
                await asyncio.sleep(5)
                await warn.delete()
        except:
            pass

# 🚨 തിരുത്തിയത്: ഭാവിയിൽ ക്രാഷ് ഉണ്ടാകാതിരിക്കാൻ getattr സുരക്ഷാ ലോക്ക് നൽകി പൂർണ്ണമാക്കിയത് 👇
@Client.on_edited_message(filters.group, group=3)
async def check_edited_messages(client: Client, message: Message):
    chat_id = message.chat.id
    locks = get_group_locks(chat_id)
    
    # getattr ഉപയോഗിച്ച് സുരക്ഷിതമായി യൂസർ ഡാറ്റ ഉണ്ടോ എന്ന് പരിശോധിക്കുന്നു
    from_user = getattr(message, "from_user", None)
    
    if locks.get("edited") and from_user:
        user_id = from_user.id
        try:
            member = await message.chat.get_member(user_id)
            if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID:
                return
            await message.delete()
        except:
            pass
