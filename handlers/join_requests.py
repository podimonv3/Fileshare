import asyncio
from pyrogram import Client, enums # 🚨 enums ഇവിടെ ഇമ്പോർട്ട് ചെയ്തിട്ടുണ്ട്
from info import OWNER_ID
from database import requests_collection, batch_collection, get_req_channel, is_maintenance_mode

# handlers/join_requests.py (അല്ലെങ്കിൽ ഒരു common helper ഫയലിൽ ഇടാം)
import math

async def auto_delete_messages(client: Client, chat_id: int, message_ids: list, info_msg_id: int, delay: int = 300):
    total_time = delay
    while delay > 0:
        await asyncio.sleep(10) # ഓരോ 10 സെക്കൻഡിലും അപ്ഡേറ്റ് ചെയ്യും
        delay -= 10
        
        # പ്രോഗ്രസ് ബാർ നിർമ്മാണം
        percentage = (delay / total_time) * 100
        completed = math.floor(percentage / 10)
        progress_bar = "█" * completed + "░" * (10 - completed)
        
        # മിനിറ്റും സെക്കൻഡും കണക്കാക്കുന്നു
        mins, secs = divmod(delay, 60)
        time_text = f"{mins:02d}:{secs:02d}"
        
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=info_msg_id,
                text=f"✨ **നിങ്ങൾ തിരഞ്ഞ ഫയലുകൾ മുകളിൽ നൽകിയിട്ടുണ്ട്!** 👇\n\n"
                     f"⚠️ **പകർപ്പവകാശ പ്രശ്നം ഒഴിവാക്കാൻ ഫയലുകൾ ഉടൻ ഡിലീറ്റ് ആകും:**\n"
                     f"⏳ `[{progress_bar}] {time_text}`\n\n"
                     f"⚡ _അതിനു മുൻപായി നിങ്ങളുടെ Saved Messages-ലേക്ക് ഫോർവേഡ് ചെയ്യുക!_"
            )
        except Exception:
            # മെസ്സേജ് ഇതിനകം ഡിലീറ്റ് ആവുകയോ എറർ വരികയോ ചെയ്താൽ ലൂപ്പ് നിർത്തും
            break

    # സമയം അവസാനിക്കുമ്പോൾ എല്ലാ മെസ്സേജുകളും ഡിലീറ്റ് ചെയ്യുന്നു
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
