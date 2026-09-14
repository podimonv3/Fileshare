import os
import psutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from info import OWNER_ID
from database import settings_collection, requests_collection, users_collection, batch_collection, get_req_channel, get_db_size
from database import (
    is_maintenance_mode, 
    set_maintenance_mode, 
    get_delete_time, 
    set_delete_time,
    is_protect_content,  # 🚨 പുതിയ ഇമ്പോർട്ട്
    set_protect_content  # 🚨 പുതിയ ഇമ്പോർട്ട്
)


# --- Add this to the bottom of handlers/admin_commands.py ---

from database import set_maintenance_mode, is_maintenance_mode

@Client.on_message(filters.command("maintenance") & filters.user(OWNER_ID))
async def toggle_maintenance(client: Client, message: Message):
    if len(message.command) < 2:
        current_status = "ON 🔴" if is_maintenance_mode() else "OFF 🟢"
        await message.reply_text(f"🛠️ **Maintenance Mode Status:** `{current_status}`\n\nTo change use:\n`/maintenance on` or `/maintenance off`")
        return
        
    action = message.command[1].lower()
    if action == "on":
        set_maintenance_mode(True)
        await message.reply_text("🔴 **Maintenance Mode Enabled!**\nRegular users will no longer be able to use the bot until it's turned off.")
    elif action == "off":
        set_maintenance_mode(False)
        await message.reply_text("🟢 **Maintenance Mode Disabled!**\nThe bot is now fully operational for everyone.")
    else:
        await message.reply_text("❌ Invalid parameter! Use `/maintenance on` or `/maintenance off`")

async def generate_stats_text() -> str:
    total_users = users_collection.count_documents({})
    total_batches = batch_collection.count_documents({})
    total_requests = requests_collection.count_documents({})
    current_channel = get_req_channel()
    
    used_db = get_db_size()
    remaining_db = max(0.0, 512.00 - used_db)
    db_perc = round((used_db / 512.00) * 100, 2)
    
    ram_limit = int(os.getenv("KOYEB_INSTANCE_MEMORY_MB", 512))
    try:
        process = psutil.Process(os.getpid())
        ram_used = round(process.memory_info().rss / (1024 * 1024), 2)
    except:
        ram_used = 0.0
    ram_perc = round((ram_used / ram_limit) * 100, 2)

    return (
        f"📊 <b>ബോട്ട് സ്റ്റാറ്റിസ്റ്റിക്സ് (Bot Stats)</b>\n\n"
        f"👤 <b>ആകെ ഉപയോക്താക്കൾ:</b> {total_users}\n"
        f"📦 <b>ആകെ ബാച്ച് ലിങ്കുകൾ:</b> {total_batches}\n"
        f"📩 <b>നിലവിലുള്ള ജോയിൻ റിക്വസ്റ്റുകൾ:</b> {total_requests}\n\n"
        f"💾 <b>MongoDB:</b> <code>{used_db} MB</code> ({db_perc}%)\n"
        f"🚀 <b>Koyeb RAM:</b> <code>{ram_used} MB</code> ({ram_perc}%)\n\n"
        f"📢 <b>ചാനൽ ഐഡി:</b> <code>{current_channel}</code>"
    )

@Client.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ <b>രീതി:</b> <code>/setchannel [ചാനൽ_ഐഡി]</code>")
        return
    try:
        new_channel_id = int(message.command[1])
        await client.get_chat(new_channel_id)
        settings_collection.update_one({'_id': 'fsub_config'}, {'$set': {'channel_id': new_channel_id}}, upsert=True)
        requests_collection.delete_many({}) 
        await message.reply_text(f"✅ <b>റിക്വസ്റ്റ് ചാനൽ മാറ്റിയിരിക്കുന്നു!</b>\n🆔 ID: <code>{new_channel_id}</code>")
    except Exception as e:
        await message.reply_text(f"❌ എറർ: {e}")

@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_command(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("⚠️ മെസ്സേജിന് മറുപടിയായി <code>/broadcast</code> ടൈപ്പ് ചെയ്യുക.")
        return
    all_users = users_collection.find()
    status_msg = await message.reply_text("📢 ബ്രോഡ്കാസ്റ്റിംഗ് ആരംഭിച്ചിരിക്കുന്നു...")
    success, failed = 0, 0
    for user in all_users:
        try:
            await client.copy_message(chat_id=user['_id'], from_chat_id=message.chat.id, message_id=message.reply_to_message.id)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await status_msg.edit_text(f"✅ <b>BR പൂർത്തിയായി!</b>\n\n👤 വിജയം: {success}\n❌ പരാജയം: {failed}")

@Client.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_command(client: Client, message: Message):
    keyboard = [[InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")]]
    await message.reply_text(await generate_stats_text(), reply_markup=InlineKeyboardMarkup(keyboard))

@Client.on_callback_query(filters.regex("^refresh_stats$"))
async def refresh_stats_callback(client: Client, query):
    if query.from_user.id != OWNER_ID:
        await query.answer("🔒 അനുവാദമില്ല!", show_alert=True)
        return
    await query.answer("🔄 വിവരങ്ങൾ പുതുക്കുന്നു...")
    keyboard = [[InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")]]
    try:
        await query.edit_message_text(await generate_stats_text(), reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        pass



# handlers/admin_commands.py-ൽ ചേർക്കുക:
def get_admin_panel_markup():
    m_status = "🔴 ON" if is_maintenance_mode() else "🟢 OFF"
    p_status = "🔒 ON" if is_protect_content() else "🔓 OFF"
    d_time = f"{get_delete_time() // 60} Min"
    
    keyboard = [
        [
            InlineKeyboardButton(f"🛠️ Maint: {m_status}", callback_data="toggle_maint"),
            InlineKeyboardButton(f"🔰 Protect: {p_status}", callback_data="toggle_protect") # 🚨 പുതിയ ബട്ടൺ
        ],
        [
            InlineKeyboardButton(f"⏳ Delete Time: {d_time}", callback_data="change_time"),
            InlineKeyboardButton("📊 Close Panel", callback_data="close_admin")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command("admin") & filters.user(OWNER_ID))
async def admin_panel_command(client: Client, message: Message):
    await message.reply_text(
        "🛠️ **WELCOME TO ADVANCED ADMIN PANEL**\n\nബോട്ടിലെ സെറ്റിങ്സുകൾ താഴെയുള്ള ബട്ടണുകൾ വഴി നിയന്ത്രിക്കാം:",
        reply_markup=get_admin_panel_markup()
    )

@Client.on_callback_query(filters.user(OWNER_ID))
async def admin_callback_handler(client: Client, query):
    data = query.data
    
    if data == "toggle_maint":
        current = is_maintenance_mode()
        set_maintenance_mode(not current)
        await query.answer(f"Maintenance Mode {'Disabled' if current else 'Enabled'}")
        await query.edit_message_reply_markup(reply_markup=get_admin_panel_markup())
        
    elif data == "toggle_protect": # 🚨 പ്രൊട്ടക്ട് കണ്ടെന്റ് ഓൺ/ഓഫ് ലോജിക്
        current = is_protect_content()
        set_protect_content(not current)
        await query.answer(f"Protect Content {'Disabled' if current else 'Enabled'}")
        await query.edit_message_reply_markup(reply_markup=get_admin_panel_markup())
        
    elif data == "change_time":
        current_time = get_delete_time()
        new_time = 600 if current_time == 300 else 300
        set_delete_time(new_time)
        await query.answer(f"Delete time changed to {new_time // 60} Minutes")
        await query.edit_message_reply_markup(reply_markup=get_admin_panel_markup())
        
    elif data == "close_admin":
        await query.message.delete()
