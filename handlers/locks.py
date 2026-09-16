import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from info import OWNER_ID
from database import settings_collection, get_group_locks, set_group_lock

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

def get_locks_markup(chat_id: int):
    locks = get_group_locks(chat_id)
    keyboard = []
    row = []
    for key, name in VALID_LOCKS.items():
        status_emoji = "🗑️" if locks.get(key) else "✅"
        row.append(InlineKeyboardButton(f"{name} {status_emoji}", callback_data=f"lck_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📊 Close Settings", callback_data="lck_close")])
    return InlineKeyboardMarkup(keyboard)


# 🛠️ കമാൻഡ് വഴി നേരിട്ട് 28 ലോക്കുകളും നിയന്ത്രിക്കാനുള്ള ബാക്കപ്പ് സിസ്റ്റം 🔒/🔓
@Client.on_message(filters.command(["lock", "unlock"]))
async def lock_unlock_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id: return

    # 1. പ്രൈവറ്റ് ചാറ്റിലാണ് (PM) അഡ്മിൻ കമാൻഡ് അടിക്കുന്നതെങ്കിൽ:
    if message.chat.type == enums.ChatType.PRIVATE:
        active = settings_collection.find_one({'_id': f'active_chat_{user_id}'})
        if not active:
            await message.reply_text("⚠️ ആദ്യം <code>/connect [ഗ്രൂപ്പ്_ഐഡി]</code> ഉപയോഗിച്ച് ഗ്രൂപ്പ് ബന്ധിപ്പിക്കുക.", parse_mode=enums.ParseMode.HTML)
            return
        chat_id = int(active['chat_id'])
        chat_title = active['chat_title']
    
    # 2. ഗ്രൂപ്പിലാണ് നേരിട്ട് കമാൻഡ് അടിക്കുന്നതെങ്കിൽ:
    else:
        chat_id = message.chat.id
        chat_title = message.chat.title
        try:
            member = await message.chat.get_member(user_id)
            if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
                return
        except: return

    # കമാൻഡിനൊപ്പം മീഡിയ ടൈപ്പ് നൽകിയിട്ടില്ലെങ്കിൽ മുഴുവൻ ലിസ്റ്റും കാണിക്കും
    if len(message.command) < 2:
        available_types = "\n".join([f"• <code>{k}</code>" for k in VALID_LOCKS.keys()])
        await message.reply_text(
            f"⚠️ **ഉപയോഗിക്കേണ്ട രീതി:**\n"
            f"🔒 ലോക്ക് ചെയ്യാൻ: <code>/lock [media_type]</code>\n"
            f"🔓 അൺലോക്ക് ചെയ്യാൻ: <code>/unlock [media_type]</code>\n\n"
            f"**Media Types (ഇവയിൽ ഒന്ന് ടൈപ്പ് ചെയ്യുക):**\n{available_types}",
            parse_mode=enums.ParseMode.HTML
        )
        return

    action = message.command[0].lower() # 'lock' അല്ലെങ്കിൽ 'unlock'
    media = message.command[1].lower()   # 'photos', 'videos' തുടങ്ങിയവ

    if media not in VALID_LOCKS:
        await message.reply_text(f"❌ തെറ്റായ മീഡിയ ടൈപ്പ്! പരിശോധിക്കാൻ വെറുതെ <code>/{action}</code> എന്ന് മാത്രം ടൈപ്പ് ചെയ്യുക.", parse_mode=enums.ParseMode.HTML)
        return

    # ഡാറ്റാബേസിൽ സ്റ്റാറ്റസ് മാറ്റുന്നു
    status = True if action == "lock" else False
    set_group_lock(chat_id, media, status)
    
    status_text = "🔒 **ലോക്ക് ചെയ്തു (Delete Mode)**" if status else "🔓 **അനുവദിച്ചു (Allow Mode)**"
    await message.reply_text(
        f"✅ <b>{chat_title}</b> എന്ന ഗ്രൂപ്പിൽ <b>{VALID_LOCKS[media].upper()}</b> ഇനി മുതൽ {status_text}!", 
        parse_mode=enums.ParseMode.HTML
    )


# 📋 ഗ്രൂപ്പിലെ മുഴുവൻ ലോക്ക് സ്റ്റാറ്റസും പരിശോധിക്കാനുള്ള പുതിയ കമാൻഡ് 🔍
@Client.on_message(filters.command(["locktypes", "locks"]))
async def view_all_lock_types(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id: return

    # 1. PM-ലാണ് കമാൻഡ് അടിക്കുന്നതെങ്കിൽ കണക്ട് ചെയ്ത ഗ്രൂപ്പ് ഐഡി എടുക്കുന്നു
    if message.chat.type == enums.ChatType.PRIVATE:
        active = settings_collection.find_one({'_id': f'active_chat_{user_id}'})
        if not active:
            await message.reply_text("⚠️ ആദ്യം <code>/connect [ഗ്രൂപ്പ്_ഐഡി]</code> ഉപയോഗിച്ച് ഗ്രൂപ്പ് ബന്ധിപ്പിക്കുക.", parse_mode=enums.ParseMode.HTML)
            return
        chat_id = int(active['chat_id'])
        chat_title = active['chat_title']
        
    # 2. ഗ്രൂപ്പിലാണ് നേരിട്ട് കമാൻഡ് അടിക്കുന്നതെങ്കിൽ
    else:
        chat_id = message.chat.id
        chat_title = message.chat.title
        try:
            member = await message.chat.get_member(user_id)
            if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
                return
        except: return

    # ഡാറ്റാബേസിൽ നിന്നും തത്സമയ ലോക്ക് വിവരങ്ങൾ എടുക്കുന്നു
    locks = get_group_locks(chat_id)
    
    # മനോഹരമായ ടെക്സ്റ്റ് ലിസ്റ്റ് നിർമ്മിക്കുന്നു
    status_text = f"📋 <b>★ {chat_title} - LOCK TYPES STATUS ★</b>\n\n"
    
    for key, name in VALID_LOCKS.items():
        # ലോക്ക് ഓൺ ആണെങ്കിൽ 🔴 LOCK (Delete Mode), ഓഫ് ആണെങ്കിൽ 🟢 ALLOW
        emoji = "🔴 <b>LOCK</b>" if locks.get(key) else "🟢 <b>ALLOW</b>"
        status_text += f"• <code>{key}</code> → {emoji}\n"
        
    status_text += f"\n🛠️ <b>മാറ്റങ്ങൾ വരുത്താൻ:</b>\n<code>/lock [type]</code> അല്ലെങ്കിൽ <code>/unlock [type]</code> ഉപയോഗിക്കുക."

    await message.reply_text(status_text, parse_mode=enums.ParseMode.HTML)


# 🚨 ഗ്രൂപ്പിലെ മുഴുവൻ മീഡിയകളും ഫീച്ചറുകളും ഒന്നിച്ച് ലോക്ക്/അൺലോക്ക് ചെയ്യാനുള്ള കമാൻഡുകൾ 🔒/🔓
@Client.on_message(filters.command(["lockall", "unlockall"]))
async def lock_unlock_all_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id: return

    # 1. PM-ലാണ് കമാൻഡ് അടിക്കുന്നതെങ്കിൽ കണക്ട് ചെയ്ത ഗ്രൂപ്പ് ഐഡി എടുക്കുന്നു
    if message.chat.type == enums.ChatType.PRIVATE:
        active = settings_collection.find_one({'_id': f'active_chat_{user_id}'})
        if not active:
            await message.reply_text("⚠️ ആദ്യം <code>/connect [ഗ്രൂപ്പ്_ഐഡി]</code> ഉപയോഗിച്ച് ഗ്രൂപ്പ് ബന്ധിപ്പിക്കുക.", parse_mode=enums.ParseMode.HTML)
            return
        chat_id = int(active['chat_id'])
        chat_title = active['chat_title']
        
    # 2. ഗ്രൂപ്പിലാണ് നേരിട്ട് കമാൻഡ് അടിക്കുന്നതെങ്കിൽ
    else:
        chat_id = message.chat.id
        chat_title = message.chat.title
        try:
            member = await message.chat.get_member(user_id)
            if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
                return
        except: return
            
    action = message.command[0].lower() # 'lockall' അല്ലെങ്കിൽ 'unlockall'
    status = True if action == "lockall" else False

    # 🔄 VALID_LOCKS ലിസ്റ്റിലുള്ള മുഴുവൻ കീകളും (Keys) പുതിയ സ്റ്റാറ്റസിലേക്ക് മാറ്റുന്നു
    updated_locks = {}
    for key in VALID_LOCKS.keys():
        updated_locks[key] = status

    # ഡാറ്റാബേസിലേക്ക് ഒന്നിച്ച് അപ്ഡേറ്റ് ചെയ്യുന്നു 💾
    settings_collection.update_one(
        {'_id': f'locks_{int(chat_id)}'}, 
        {'$set': {'locks': updated_locks}}, 
        upsert=True
    )
    
    if status:
        msg_text = f"🚨 <b>{chat_title} - EMERGENCY LOCKDOWN!</b> 🚨\n\n🔒 ഗ്രൂപ്പിലെ മുഴുവൻ മീഡിയകളും, സർവീസ് നോട്ടിഫിക്കേഷനുകളും, ടെക്സ്റ്റ് സ്റ്റൈലുകളും ഒന്നിച്ച് <b>ലോക്ക് ചെയ്തിരിക്കുന്നു (Emergency Lockdown)</b>. ഇനി അഡ്മിൻമാർക്ക് മാത്രമേ ഗ്രൂപ്പിൽ എന്തെങ്കിലും അയക്കാൻ സാധിക്കൂ!"
    else:
        msg_text = f"🔓 <b>{chat_title} - LOCKDOWN LIFTED!</b> 🔓\n\n✅ ഗ്രൂപ്പിലെ മുഴുവൻ ലോക്കുകളും ഒന്നിച്ച് <b>ഒഴിവാക്കിയിരിക്കുന്നു</b>. സാധാരണ മെമ്പർമാർക്ക് ഇനി മുതൽ ഗ്രൂപ്പിൽ എല്ലാം അയക്കാവുന്നതാണ്."

    await message.reply_text(msg_text, parse_mode=enums.ParseMode.HTML)



@Client.on_message(filters.command("connect") & filters.private)
async def connect_group_command(client: Client, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text("⚠️ **രീതി:**\n<code>/connect -10022334455</code>", parse_mode=enums.ParseMode.HTML)
        return
    try:
        chat_id = int(message.command[1])
        chat_title = (await client.get_chat(chat_id)).title
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and user_id != OWNER_ID:
            await message.reply_text("❌ നിങ്ങൾ ആ ഗ്രൂപ്പിലെ അഡ്മിൻ അല്ല!")
            return
        settings_collection.update_one({'_id': f'active_chat_{user_id}'}, {'$set': {'chat_id': chat_id, 'chat_title': chat_title}}, upsert=True)
        await message.reply_text(f"✅ **കണക്ട് ചെയ്തു!**\n👥 ഗ്രൂപ്പ്: <b>{chat_title}</b>\n\nഇനി PM-ൽ <code>/settings</code> എന്ന് അടിക്കുക.", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"❌ കണക്ഷൻ പരാജയപ്പെട്ടു! Error: {e}")

@Client.on_message(filters.command("settings") & filters.private)
async def group_settings_panel(client: Client, message: Message):
    user_id = message.from_user.id
    active = settings_collection.find_one({'_id': f'active_chat_{user_id}'})
    if not active:
        await message.reply_text("⚠️ ആദ്യം <code>/connect [ഗ്രൂപ്പ്_ഐഡി]</code> ഉപയോഗിക്കുക.", parse_mode=enums.ParseMode.HTML)
        return
    chat_id = int(active['chat_id'])
    await message.reply_text(
        f"⚙️ <b>★ {active['chat_title']} - SETTINGS ★</b>\n\n✅ = Allow\n🗑️ = Delete",
        reply_markup=get_locks_markup(chat_id), parse_mode=enums.ParseMode.HTML
    )

@Client.on_callback_query(filters.regex("^lck_"))
async def locks_callback_handler(client: Client, query):
    user_id = query.from_user.id
    active = settings_collection.find_one({'_id': f'active_chat_{user_id}'})
    if not active:
        await query.answer("❌ കണക്ഷൻ കണ്ടെത്തിയില്ല!", show_alert=True)
        return
    chat_id = int(active['chat_id'])
    action = query.data.split("_")[1]
    if action == "close":
        await query.message.delete()
        return
    locks = get_group_locks(chat_id)
    new_status = not locks.get(action, False)
    set_group_lock(chat_id, action, new_status)
    await query.answer(f"{VALID_LOCKS[action]} ലോക്ക് മാറ്റി!")
    try: await query.edit_message_reply_markup(reply_markup=get_locks_markup(chat_id))
    except: pass



@Client.on_message(filters.group, group=2)
async def check_group_media_locks(client: Client, message: Message):
    chat_id = int(message.chat.id)
    locks = get_group_locks(chat_id)

    if getattr(message, "sender_chat", None) and message.sender_chat.type == enums.ChatType.CHANNEL:
        if locks.get("channel") and not getattr(message, "is_automatic_forward", False):
            try: await message.delete(); return
            except: pass

    should_delete = False
    media_name = ""

    if getattr(message, "forward_from_chat", None) and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        if locks.get("fwd_channel"): should_delete = True

    if getattr(message, "new_chat_members", None) and locks.get("new_members"): should_delete = True
    elif getattr(message, "left_chat_member", None) and locks.get("left_members"): should_delete = True
    elif getattr(message, "new_chat_title", None) and locks.get("title_changed"): should_delete = True
    elif (getattr(message, "new_chat_photo", None) or getattr(message, "delete_chat_photo", None)) and locks.get("photo_changed"): should_delete = True
    elif getattr(message, "pinned_message", None) and locks.get("pinned"): should_delete = True
    elif (getattr(message, "video_chat_started", None) or getattr(message, "video_chat_ended", None) or getattr(message, "video_chat_members_invited", None) or getattr(message, "video_chat_scheduled", None)) and locks.get("video_chat"): should_delete = True

    elif getattr(message, "from_user", None):
        user_id = message.from_user.id
        try:
            member = await message.chat.get_member(user_id)
            if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID:
                return
        except: return

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

        elif (getattr(message, "text", None) or getattr(message, "caption", None)):
            entities = message.entities or message.caption_entities
            if entities:
                for ent in entities:
                    if ent.type == enums.MessageEntityType.MENTION and locks.get("usernames"): should_delete = True; media_name = VALID_LOCKS["usernames"]
                    elif ent.type == enums.MessageEntityType.HASHTAG and locks.get("hashtags"): should_delete = True; media_name = VALID_LOCKS["hashtags"]
                    elif ent.type == enums.MessageEntityType.BOT_COMMAND and locks.get("commands"): should_delete = True; media_name = VALID_LOCKS["commands"]
                    elif ent.type == enums.MessageEntityType.EMAIL and locks.get("emails"): should_delete = True; media_name = VALID_LOCKS["emails"]
                    elif ent.type in [enums.MessageEntityType.URL, enums.MessageEntityType.TEXT_LINK] and locks.get("links"): should_delete = True; media_name = VALID_LOCKS["links"]
                    elif ent.type in [enums.MessageEntityType.BOLD, enums.MessageEntityType.ITALIC, enums.MessageEntityType.SPOILER, enums.MessageEntityType.CODE] and locks.get("text_styles"): should_delete = True; media_name = VALID_LOCKS["text_styles"]
                        
    if should_delete:
        try:
            await message.delete()
        except: 
            pass  
    

@Client.on_edited_message(filters.group, group=3)
async def check_edited_messages(client: Client, message: Message):
    chat_id = int(message.chat.id)
    locks = get_group_locks(chat_id)
    from_user = getattr(message, "from_user", None)
    if locks.get("edited") and from_user:
        user_id = from_user.id
        try:
            member = await message.chat.get_member(user_id)
            if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id == OWNER_ID: return
            await message.delete()
        except: pass

