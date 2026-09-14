import asyncio
from pyrogram import Client, enums # 🚨 enums ഇവിടെ ഇമ്പോർട്ട് ചെയ്തിട്ടുണ്ട്
from info import OWNER_ID
from database import requests_collection, batch_collection, get_req_channel, is_maintenance_mode

# Auto Delete Helper Function
async def auto_delete_messages(client: Client, chat_id: int, message_ids: list, info_msg_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, info_msg_id)
    except:
        pass
    for msg_id in message_ids:
        try:
            await client.delete_messages(chat_id, msg_id)
        except:
            continue

@Client.on_chat_join_request()
async def handle_join_request(client: Client, request):
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    # 🚨 1. Maintenance Mode സെറ്റ് ചെയ്തിട്ടുണ്ടെങ്കിൽ സാധാരണ ഉപയോക്താക്കൾക്ക് മുന്നറിയിപ്പ് നൽകി ഇവിടെ വെച്ച് തടയുന്നു
    if is_maintenance_mode() and user_id != OWNER_ID:
        try:
            await client.send_message(
                chat_id=user_id,
                text="⚠️ **ബോട്ട് അറ്റകുറ്റപ്പണിയിലാണ് (Under Maintenance)**\n\nനിങ്ങളുടെ ജോയിൻ റിക്വസ്റ്റ് ലഭിച്ചിട്ടുണ്ട്. ബോട്ടിലെ പണികൾ പൂർത്തിയായ ഉടൻ തന്നെ നിങ്ങൾ തിരഞ്ഞ ഫയലുകൾ ഓട്ടോമാറ്റിക് ആയി അയച്ചു തരുന്നതാണ്! 🔄"
            )
        except:
            pass
        return

    current_channel = get_req_channel()
    if chat_id == current_channel:
        requests_collection.update_one(
            {'user_id': user_id, 'channel_id': chat_id},
            {'$set': {'user_id': user_id, 'channel_id': chat_id, 'status': 'requested'}},
            upsert=True
        )
        
        user_pending = requests_collection.find_one({'user_id': user_id, 'channel_id': chat_id})
        if user_pending and 'batch_id' in user_pending:
            batch_id = user_pending['batch_id']
            batch_data = batch_collection.find_one({'batch_id': batch_id})
            
            if batch_data:
                from_chat = batch_data['from_chat']
                start_id = batch_data['start_id']
                end_id = batch_data['end_id']
                
                try:
                    # 🚨 parse_mode=enums.ParseMode.HTML സുരക്ഷിതമായി ആഡ് ചെയ്തു
                    info_msg = await client.send_message(
                        chat_id=user_id,
                        text="✨ <b>നിങ്ങളുടെ ജോയിൻ റിക്വസ്റ്റ് ലഭിച്ചിരിക്കുന്നു! നിങ്ങൾ തിരഞ്ഞ ഫയലുകൾ താഴെ നൽകുന്നു:</b> 👇\n\n⚠️ <b>ശ്രദ്ധിക്കുക:</b> ഈ ഫയലുകൾ 5 മിനിറ്റിനുള്ളിൽ തനിയെ ഡിലീറ്റ് ആകുന്നതാണ്!",
                        parse_mode=enums.ParseMode.HTML
                    )
                    
                    sent_msg_ids = []
                    for msg_id in range(start_id, end_id + 1):
                        copied_msg = await client.copy_message(chat_id=user_id, from_chat_id=from_chat, message_id=msg_id, protect_content=True)
                        sent_msg_ids.append(copied_msg.id)
                    
                    asyncio.create_task(auto_delete_messages(client, user_id, sent_msg_ids, info_msg.id))
                    requests_collection.update_one({'user_id': user_id, 'channel_id': chat_id}, {'$unset': {'batch_id': ""}})
                except:
                    pass
