import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from info import OWNER_ID
from database import get_group_locks, set_group_lock

# 🔒 ലോക്ക് ലിസ്റ്റുകൾ
VALID_LOCKS = {
    "photos": "Photos",
    "videos": "Videos",
    "stickers": "Stickers / Emojis",
    "voice": "Voice Messages",
    "audio": "Audios / Music",
    "document": "Documents",
    "animation": "GIFs / Animations",
    "poll": "Polls",
    "video_note": "Video Messages",
    "contact": "Contacts",
    "location": "Locations",
    "inline": "Inline Bots",
    "story": "Stories",
    "game": "Games",
    "channel": "As a Channel"
}

# 🎛️ ബട്ടണുകൾ നിർമ്മിക്കുന്ന ഹെൽപ്പർ ഫങ്ക്ഷൻ
def get_locks_markup(chat_id: int):
    locks = get_group_locks(chat_id)
    keyboard = []
    
    # 2 ബട്ടണുകൾ വീതം ഒരു വരിയിൽ വരുന്ന രീതിയിൽ ക്രമീകരിക്കുന്നു
    row = []
    for key, name in VALID_LOCKS.items():
        # ലോക്ക് ഓൺ ആണെങ്കിൽ 🗑️ (Delete), ഓഫ് ആണെങ്കിൽ ✅ (Allow) കാണിക്കും
        status_emoji = "🗑️" if locks.get(key) else "✅"
        button_text = f"{name} {status_emoji}"
        
        row.append(InlineKeyboardButton(button_text, callback_data=f"lck_{key}_{chat_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("📊 Close Settings", callback_data=f"lck_close_{chat_id}")])
    return InlineKeyboardMarkup(keyboard)


# 1️⃣ /settings കമാൻഡ് വഴി വിഷ്വൽ കൺട്രോൾ പാനൽ ഓപ്പൺ ചെയ്യുന്നു 🎛️
@Client.on_message(filters.command("settings") & filters.group)
async def group_settings_panel(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    
    if not user_id: return

    # അഡ്മിൻ ചെക്കിങ്
    try:
        member = await message.chat.get_member(user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
            return
    except:
        return

    await message.reply_text(
        f"⚙️ <b>★ {message.chat.title} - SETTINGS ★</b>\n\n"
        f"ഗ്രൂപ്പിൽ മെമ്പർമാർ അയക്കാൻ പാടില്ലാത്ത മീഡിയകൾ താഴെയുള്ള ബട്ടണുകൾ വഴി നിയന്ത്രിക്കാം:\n"
        f"✅ = <b>Allow (അനുവദിച്ചു)</b>\n"
        f"🗑️ = <b>Delete (ലോക്ക് ചെയ്തു)</b>",
        reply_markup=get_locks_markup(chat_id),
        parse_mode=enums.ParseMode.HTML
    )


# 2️⃣ ബട്ടണുകളിൽ ക്ലിക്ക് ചെയ്യുമ്പോൾ ഉള്ള ആക്ഷനുകൾ കൈകാര്യം ചെയ്യുന്നു 🔄
@Client.on_callback_query(filters.regex("^lck_"))
async def locks_callback_handler(client: Client, query):
    data_split = query.data.split("_")
    action = data_split[1] # കോൾബാക്ക് ടൈപ്പ്
    
    # സെക്യൂരിറ്റിക്കായി ഗ്രൂപ്പ് ഐഡി കോൾബാക്കിൽ നിന്ന് എടുക്കുന്നു
    try:
        chat_id = int(data_split[2])
    except:
        return

    user_id = query.from_user.id

    # ബട്ടൺ ഞെക്കിയത് അഡ്മിൻ തന്നെയാണോ എന്ന് ഉറപ്പുവരുത്തുന്നു 🔒
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
            await query.answer("🔒 ക്ഷമിക്കണം, അഡ്മിൻമാർക്ക് മാത്രമേ ഇതിന് അനുവാദമുള്ളൂ!", show_alert=True)
            return
    except:
        return

    if action == "close":
        await query.message.delete()
        return

    # നിലവിലെ ലോക്ക് സ്റ്റാറ്റസ് തിരിച്ചു മാറ്റുന്നു (True -> False / False -> True)
    locks = get_group_locks(chat_id)
    current_status = locks.get(action, False)
    new_status = not current_status
    
    set_group_lock(chat_id, action, new_status)
    
    # ബട്ടൺ ടോപ്പ്-അപ്പ് മെസ്സേജ് കാണിക്കുന്നു
    alert_text = f"{VALID_LOCKS[action]} ലോക്ക് ചെയ്തു! (Delete Mode)" if new_status else f"{VALID_LOCKS[action]} അനുവദിച്ചു! (Allow Mode)"
    await query.answer(alert_text)
    
    # ബട്ടണിലെ ഇമോജികൾ തത്സമയം അപ്ഡേറ്റ് ചെയ്യുന്നു 🔄
    try:
        await query.edit_message_reply_markup(reply_markup=get_locks_markup(chat_id))
    except:
        pass


# 3️⃣ ഗ്രൂപ്പിൽ വരുന്ന മെസ്സേജുകൾ പരിശോധിച്ച് ലോക്ക് ചെയ്തവ ഡിലീറ്റ് ചെയ്യുന്ന സിസ്റ്റം (മാറ്റമില്ല)
@Client.on_message(filters.group, group=2)
async def check_group_media_locks(client: Client, message: Message):
    chat_id = message.chat.id
    locks = get_group_locks(chat_id)

    if message.sender_chat and message.sender_chat.type == enums.ChatType.CHANNEL:
        if locks.get("channel") and not message.is_automatic_forward:
            try: await message.delete(); return
            except: pass

    if not message.from_user: return
    user_id = message.from_user.id

    try:
        member = await message.chat.get_member(user_id)
        if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID:
            return
    except:
        return

    should_delete = False
    media_name = ""

    if message.photo and locks.get("photos"): should_delete = True; media_name = VALID_LOCKS["photos"]
    elif message.video and locks.get("videos"): should_delete = True; media_name = VALID_LOCKS["videos"]
    elif message.sticker and locks.get("stickers"): should_delete = True; media_name = VALID_LOCKS["stickers"]
    elif message.voice and locks.get("voice"): should_delete = True; media_name = VALID_LOCKS["voice"]
    elif message.audio and locks.get("audio"): should_delete = True; media_name = VALID_LOCKS["audio"]
    elif message.document and locks.get("document"): should_delete = True; media_name = VALID_LOCKS["document"]
    elif message.animation and locks.get("animation"): should_delete = True; media_name = VALID_LOCKS["animation"]
    elif message.poll and locks.get("poll"): should_delete = True; media_name = VALID_LOCKS["poll"]
    elif message.video_note and locks.get("video_note"): should_delete = True; media_name = VALID_LOCKS["video_note"]
    elif message.contact and locks.get("contact"): should_delete = True; media_name = VALID_LOCKS["contact"]
    elif message.location and locks.get("location"): should_delete = True; media_name = VALID_LOCKS["location"]
    elif message.via_bot and locks.get("inline"): should_delete = True; media_name = VALID_LOCKS["inline"]
    elif message.story and locks.get("story"): should_delete = True; media_name = VALID_LOCKS["story"]
    elif message.game and locks.get("game"): should_delete = True; media_name = VALID_LOCKS["game"]

    if should_delete:
        try:
            await message.delete()
            warn = await client.send_message(
                chat_id=chat_id,
                text=f"⚠️ {message.from_user.mention}, ഈ ഗ്രൂപ്പിൽ <b>{media_name}</b> അയക്കാൻ അനുവാദമില്ല! അത് ഡിലീറ്റ് ചെയ്തിട്ടുണ്ട്.",
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(5)
            await warn.delete()
        except:
            pass

