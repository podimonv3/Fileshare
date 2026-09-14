import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from info import LOG_CHANNEL_ID

# 🚫 സ്പാം വാക്കുകളും ഇമോജികളും
BAD_WORDS_PATTERN = re.compile(r'(xvideos|xnxxn|xnxx|xhamster|xxx videos|തുണ്ട്|porn\s*videos)', re.IGNORECASE)
ADULT_EMOJIS = ["🍑", "🍆", "🍌", "💦", "💋", "👙", "🔞", "🥵", "👅"]

@Client.on_message(filters.text & filters.group, group=1)
async def anti_spam_handler(client: Client, message: Message):
    if not message.text or not message.from_user:
        return

    message_text = message.text
    user = message.from_user
    chat = message.chat

    # 👑 അഡ്മിൻമാർ അയക്കുന്ന മെസ്സേജുകൾ ബോട്ട് പരിശോധിക്കില്ല
    try:
        member = await chat.get_member(user.id)
        if member.status in ['owner', 'administrator']:
            return
    except:
        return

    # 18+ ഇമോജികൾ ഉണ്ടോ എന്ന് നോക്കുന്നു
    has_adult_emoji = any(emoji in message_text for emoji in ADULT_EMOJIS)

    # 🔗 ടെലഗ്രാം ലിങ്കുകളും മറ്റ് വെബ്‌സൈറ്റ് ലിങ്കുകളും കണ്ടുപിടിക്കാനുള്ള ഫിൽട്ടർ (Anti-Link)
    # t.me/, telegram.me, http://, https:// എന്നിവയെല്ലാം ഇത് തടയും
    contains_link = (
        "t.me/" in message_text.lower() or 
        "telegram.me/" in message_text.lower() or 
        "http://" in message_text.lower() or 
        "https://" in message_text.lower()
    )

    # 🚫 ഇതിൽ ഏതെങ്കിലും ഒന്ന് കണ്ടെത്തിയാൽ ബോട്ട് ആക്ഷൻ എടുക്കും
    if BAD_WORDS_PATTERN.search(message_text) or contains_link or has_adult_emoji:
        action_type = "Link Spam" if contains_link else "18+ Adult Content"
        
        try:
            # 1. സ്പാമറെ ഗ്രൂപ്പിൽ മ്യൂട്ട് ചെയ്യുന്നു (മെസ്സേജ് അയക്കാൻ പറ്റാത്ത രീതിയിൽ ബ്ലോക്ക് ചെയ്യുന്നു)
            await chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
            # 2. ഗ്രൂപ്പിൽ വന്ന ആ സ്പാം മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു
            await message.delete()
            
            # 3. ഗ്രൂപ്പിൽ ഒരു മുന്നറിയിപ്പ് മെസ്സേജ് നൽകുന്നു
            warn_msg = await client.send_message(
                chat_id=chat.id,
                text=f"⚠️ {user.mention}, ഗ്രൂപ്പിൽ അനാവശ്യ ലിങ്കുകളോ സ്പാം മെസ്സേജുകളോ അയക്കാൻ അനുവാദമില്ല! നിങ്ങൾ മ്യൂട്ട് ചെയ്യപ്പെട്ടിരിക്കുന്നു."
            )
            # ഗ്രൂപ്പിലെ മുന്നറിയിപ്പ് മെസ്സേജ് ചാറ്റ് ബോക്സ് എപ്പോഴും ക്ലീൻ ആയിരിക്കാൻ 10 സെക്കൻഡിന് ശേഷം തനിയെ ഡിലീറ്റ് ആകും ⏱️
            asyncio.create_task(asyncio.sleep(10))
            try:
                await warn_msg.delete()
            except:
                pass
                
        except Exception as e:
            print(f"Mute/Delete Error: {e}")

        # 4. അഡ്മിൻ ലോഗ് ചാനലിലേക്ക് അയക്കാനുള്ള റിപ്പോർട്ട് തയ്യാറാക്കുന്നു
        pm_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        report_text = (
            "🚨 **Spam & Anti-Link Mute Report** 🚨\n\n"
            f"👤 **പേര്:** {user.first_name}\n"
            f"🆔 **Telegram ID:** `{user.id}`\n"
            f"🔗 **PM Link:** [ഇവിടെ ക്ലിക്ക് ചെയ്യുക]({pm_link})\n"
            f"💬 **വന്ന ഗ്രൂപ്പ്:** {chat.title}\n"
            f"🚫 **ലംഘനം (Reason):** `{action_type}`\n\n"
            f"📝 **അയച്ച സ്പാം മെസ്സേജ്:**\n_{message_text}_"
        )
        
        try:
            await client.send_message(chat_id=LOG_CHANNEL_ID, text=report_text)
        except Exception as e:
            print(f"Log channel error: {e}")

