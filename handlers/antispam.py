import re
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from info import LOG_CHANNEL_ID

BAD_WORDS_PATTERN = re.compile(r'(xvideos|xnxxn|xnxx|xhamster|xxx videos|തുണ്ട്|porn\s*videos)', re.IGNORECASE)
ADULT_EMOJIS = ["🍑", "🍆", "🍌", "💦", "💋", "👙", "🔞", "🥵", "👅"]

@Client.on_message(filters.text & filters.group, group=1)
async def anti_spam_handler(client: Client, message: Message):
    if not message.text or not message.from_user:
        return

    message_text = message.text
    user = message.from_user
    chat = message.chat

    try:
        member = await chat.get_member(user.id)
        if member.status in ['owner', 'administrator']:
            return
    except:
        return

    has_adult_emoji = any(emoji in message_text for emoji in ADULT_EMOJIS)

    if BAD_WORDS_PATTERN.search(message_text) or "t.me/+" in message_text or "t.me/joinchat" in message_text or has_adult_emoji:
        try:
            await chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
            await message.delete()
        except Exception as e:
            print(f"Mute Error: {e}")

        pm_link = f"https://t.me{user.username}" if user.username else f"tg://user?id={user.id}"
        report_text = (
            "🚨 **18+ Spam Mute Report** 🚨\n\n"
            f"👤 **പേര്:** {user.first_name}\n"
            f"🆔 **Telegram ID:** `{user.id}`\n"
            f"🔗 **PM Link:** [ഇവിടെ ക്ലിക്ക് ചെയ്യുക]({pm_link})\n"
            f"💬 **വന്ന ഗ്രൂപ്പ്:** {chat.title}\n\n"
            f"📝 **അയച്ച സ്പാം മെസ്സേജ്:**\n_{message_text}_"
        )
        try:
            await client.send_message(chat_id=LOG_CHANNEL_ID, text=report_text)
        except Exception as e:
            print(f"Log error: {e}")
