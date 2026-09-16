import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from info import LOG_CHANNEL_ID

# 🚫 സ്പാം വാക്കുകളും ഇമോജികളും
BAD_WORDS_PATTERN = re.compile(r'(xvideos|xnxxn|xnxx|xhamster|xxx videos|തുണ്ട്|porn\s*videos)', re.IGNORECASE)
ADULT_EMOJIS = ["🍑", "🍆", "🍌", "💦", "💋", "👙", "🔞", "🥵", "👅", "👆"]

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

    # 🚫 ബാഡ് വേർഡ്സ് ഉണ്ടോ എന്ന് നോക്കുന്നു
    has_bad_word = bool(BAD_WORDS_PATTERN.search(message_text))

    # 🔗 ടെലഗ്രാം ലിങ്കുകളും മറ്റ് വെബ്‌സൈറ്റ് ലിങ്കുകളും കണ്ടുപിടിക്കാനുള്ള ഫിൽട്ടർ (Anti-Link)
    contains_link = (
        "t.me/" in message_text.lower() or 
        "telegram.me/" in message_text.lower() or 
        "http://" in message_text.lower() or 
        "https://" in message_text.lower()
    )

    # 🛠️ ആക്ഷൻ എടുക്കണോ എന്ന് തീരുമാനിക്കുന്നു
    if has_bad_word or has_adult_emoji or contains_link:
        
        try:
            # 1. ലിങ്ക് മാത്രമാണെങ്കിൽ ഡിലീറ്റ് ചെയ്യുക മാത്രം ചെയ്യുന്നു (No Mute, No Log)
            if contains_link and not (has_bad_word or has_adult_emoji):
                await message.delete()
                return  # ഇവിടെ വെച്ച് ഫംഗ്ഷൻ നിർത്തുന്നു, ലോഗ് അയക്കില്ല 🛑
            
            # 2. ബാഡ് വേർഡ്സ് അല്ലെങ്കിൽ മോശം ഇമോജി ഉണ്ടെങ്കിൽ ഡിലീറ്റ് ചെയ്യുകയും മ്യൂട്ട് ചെയ്യുകയും ചെയ്യുന്നു
            else:
                action_type = "Muted for 18+ Content"
                # മെമ്പറെ ഗ്രൂപ്പിൽ മ്യൂട്ട് ചെയ്യുന്നു
                await chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
                # മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു
                await message.delete()
                
        except Exception as e:
            print(f"Action Error: {e}")
            return

        # 3. മ്യൂട്ട് ചെയ്യുമ്പോൾ മാത്രം അഡ്മിൻ ലോഗ് ചാനലിലേക്ക് റിപ്പോർട്ട് അയക്കുന്നു 🚨
        pm_link = f"https://t.me{user.username}" if user.username else f"tg://user?id={user.id}"
        report_text = (
            "🚨 **Anti-Spam Filter Report** 🚨\n\n"
            f"👤 **പേര്:** {user.first_name}\n"
            f"🆔 **Telegram ID:** `{user.id}`\n"
            f"🔗 **PM Link:** [ഇവിടെ ക്ലിക്ക് ചെയ്യുക]({pm_link})\n"
            f"💬 **വന്ന ഗ്രൂപ്പ്:** {chat.title}\n"
            f"🚫 **എടുത്ത ആക്ഷൻ:** `{action_type}`\n\n"
            f"📝 **അയച്ച മെസ്സേജ്:**\n_{message_text}_"
        )
        
        try:
            await client.send_message(chat_id=LOG_CHANNEL_ID, text=report_text)
        except Exception as e:
            print(f"Log channel error: {e}")

