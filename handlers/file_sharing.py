import base64
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from info import OWNER_ID
from database import batch_collection, requests_collection, get_req_channel, add_user
from handlers.join_requests import auto_delete_messages

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    current_channel = get_req_channel()
    
    # 1️⃣ ലിങ്ക് വഴി അല്ലാതെ വെറുതെ /start അയക്കുമ്പോൾ വരുന്ന ഭാഗം
    if len(message.command) == 1:
        # ചാനൽ, ഗ്രൂപ്പ് ലിങ്കുകൾ അടങ്ങിയ ബട്ടണുകൾ
        user_keyboard = [
            [
                InlineKeyboardButton("🎈 𝕮𝖍𝖆𝖓𝖓𝖊𝖑 🎈", url="https://t.me"),
                InlineKeyboardButton("🎈 𝕲𝖗𝖔𝖚𝖕 🎈", url="https://t.me")
            ],
            [
                InlineKeyboardButton("✨️ ʀʊʟɛֆ ✨️", url="https://telegra.ph")
            ]
        ]
        
        # 👑 മെസ്സേജ് അയച്ചത് ബോട്ട് അഡ്മിൻ (OWNER) ആണെങ്കിൽ കമാൻഡ് ലിസ്റ്റ് കൂടി നൽകുന്നു
        if user_id == OWNER_ID:
            admin_text = (
                "👋 **ഹലോ അഡ്മിൻ, സുഖമാണോ!**\n\n"
                "ഞാൻ ഒരു അഡ്വാന്‍സ്ഡ് ജോയിൻ റിക്വസ്റ്റ് ഫീച്ചറുള്ള ഫയൽ ഷെയറിങ് ബോട്ട് ആണ്. 📂\n\n"
                "🛠️ **<u>ADMIN COMMANDS LIST</u>**\n\n"
                "📢 `/broadcast` - ഒരു മെസ്സേജിന് മറുപടിയായി (Reply) ഈ കമാൻഡ് ഉപയോഗിച്ചാൽ എല്ലാ ഉപയോക്താക്കൾക്കും ആ മെസ്സേജ് ബ്രോഡ്കാസ്റ്റ് ചെയ്യാം.\n"
                "🆔 `/setchannel [ചാനൽ_ഐഡി]` - റിക്വസ്റ്റ് ചോദിക്കേണ്ട പുതിയ ചാനൽ ഐഡി സെറ്റ് ചെയ്യാൻ.\n"
                "📊 `/stats` - ബോട്ടിന്റെ നിലവിലെ യൂസർമാരുടെയും, ഡാറ്റാബേസിന്റെയും, റാം വിവരങ്ങളും പരിശോധിക്കാൻ.\n"
                "📂 **Batch Link ക്രിയേറ്റ് ചെയ്യാൻ:** ചാനലിലെ ആദ്യത്തെ ഫയലും അവസാനത്തെ ഫയലും ബോട്ടിലേക്ക് ഫോർവേഡ് ചെയ്യുക."
            )
            await message.reply_text(text=admin_text, reply_markup=InlineKeyboardMarkup(user_keyboard), parse_mode="HTML")
        
        # 👥 മെസ്സേജ് അയച്ചത് സാധാരണ യൂസർ ആണെങ്കിൽ ഉള്ള മെസ്സേജ്
        else:
            user_text = (
                "👋 **ഹലോ! ഞങ്ങളുടെ ബോട്ടുമായി ബന്ധപ്പെട്ട വിവരങ്ങൾ താഴെ നൽകുന്നു:**\n\n"
                "আমি একটি উন্নত জয়েন রিকোয়েস্ট ফিচারযুক্ত ফাইল শেয়ারিং বট। 📂\n"
                "ലിങ്കുകൾ വഴി ഫയലുകൾ നേടാൻ താഴെ കാണുന്ന ചാനലുകളിലും ഗ്രൂപ്പുകളിലും ജോയിൻ ചെയ്യുക 👇"
            )
            await message.reply_text(text=user_text, reply_markup=InlineKeyboardMarkup(user_keyboard))
        return

    # 2️⃣ ഫയൽ ലിങ്ക് വഴി വരികയാണെങ്കിൽ ഉള്ള ഭാഗം (ഇതിൽ മാറ്റമില്ല)
    batch_id = message.command[1]
    is_joined = False
    try:
        member = await client.get_chat_member(chat_id=current_channel, user_id=user_id)
        if member.status in ['member', 'administrator', 'owner']:
            is_joined = True
    except:
        pass
        
    has_requested = False
    if not is_joined and current_channel:
        db_check = requests_collection.find_one({'user_id': user_id, 'channel_id': current_channel, 'status': 'requested'})
        if db_check:
            has_requested = True

    if not is_joined and not has_requested:
        requests_collection.update_one(
            {'user_id': user_id, 'channel_id': current_channel},
            {'$set': {'batch_id': batch_id, 'status': 'pending'}},
            upsert=True
        )
        
        try:
            invite_link = await client.create_chat_invite_link(chat_id=current_channel, creates_join_request=True)
            link = invite_link.invite_link
        except:
            link = "https://t.me"

        keyboard = [[InlineKeyboardButton("📩 Request to Join Channel", url=link)]]
        await message.reply_text(
            "⚠️ <b>ഫയലുകൾ ലഭിക്കുന്നതിനായി താഴെ കാണുന്ന ചാനലിലേക്ക് Join Request അയക്കുക!</b>\n\n"
            "👇 <i>താഴെയുള്ള ബട്ടൺ അമർത്തി റിക്വസ്റ്റ് കൊടുക്കുന്ന നിമിഷം ബോട്ട് ഫയലുകൾ അയച്ചു തരും.</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    batch_data = batch_collection.find_one({'batch_id': batch_id})
    if batch_data:
        from_chat = batch_data['from_chat']
        start_id = batch_data['start_id']
        end_id = batch_data['end_id']
        
        info_msg = await message.reply_text("✨ <b>താങ്കൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു!</b> 👇\n\n⚠️ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയലുകൾ 5 മിനിറ്റിനുള്ളിൽ തനിയെ ഡിലീറ്റ് ആകുന്നതാണ്!", parse_mode="HTML")
        
        sent_msg_ids = []
        for msg_id in range(start_id, end_id + 1):
            try:
                copied_msg = await client.copy_message(chat_id=message.chat.id, from_chat_id=from_chat, message_id=msg_id, protect_content=True)
                sent_msg_ids.append(copied_msg.id)
            except:
                continue
        
        asyncio.create_task(auto_delete_messages(client, message.chat.id, sent_msg_ids, info_msg.id))
    else:
        await message.reply_text("❌ തെറ്റായ ലിങ്ക് അല്ലെങ്കിൽ ഈ ബാച്ച് നിലവിലില്ല!")



# Admin Batch File Forwarding Lock
@Client.on_message(filters.forwarded & filters.user(OWNER_ID) & (filters.document | filters.photo | filters.video | filters.audio | filters.sticker | filters.text))
async def handle_forwarded_files(client: Client, message: Message):
    chat_id = message.forward_from_chat.id if message.forward_from_chat else message.chat.id
    msg_id = message.forward_from_message_id if message.forward_from_message_id else message.id
    user_id = message.from_user.id
    
    if not hasattr(client, "user_data_store"):
        client.user_data_store = {}

    if user_id not in client.user_data_store:
        client.user_data_store[user_id] = {'chat_id': chat_id, 'start_msg_id': msg_id}
        await message.reply_text("📥 <b>ആദ്യത്തെ ഫയൽ സ്വീകരിച്ചിരിക്കുന്നു!</b>\n\nഇനി അവസാന ഫയൽ ഫോർവേഡ് ചെയ്യൂ...")
    else:
        first_file_data = client.user_data_store[user_id]
        if first_file_data['chat_id'] != chat_id:
            await message.reply_text("❌ രണ്ട് ഫയലുകളും ഒരേ ചാനലിൽ നിന്നായിരിക്കണം!")
            del client.user_data_store[user_id]
            return
            
        start_id = min(first_file_data['start_msg_id'], msg_id)
        end_id = max(first_file_data['start_msg_id'], msg_id)
        
        unique_str = f"{chat_id}_{start_id}_{end_id}"
        batch_id = base64.urlsafe_b64encode(unique_str.encode()).decode().replace("=", "")
        
        batch_collection.update_one(
            {'batch_id': batch_id},
            {'$set': {'batch_id': batch_id, 'from_chat': chat_id, 'start_id': start_id, 'end_id': end_id}},
            upsert=True
        )
        
        bot_info = await client.get_me()
        batch_link = f"https://t.me{bot_info.username}?start={batch_id}"
        
        await message.reply_text(f"✅ <b>Batch നിർമ്മിച്ചിരിക്കുന്നു!</b>\n🔗 <b>Batch ലിങ്ക്:</b> {batch_link}")
        del client.user_data_store[user_id]

