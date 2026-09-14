from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_message(filters.new_chat_members)
async def welcome_new_member(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue

        user_mention = member.mention
        welcome_keyboard = [
            [
                InlineKeyboardButton("🎈 𝕮𝖍𝖆𝖓𝖓𝖊𝖑 🎈", url="https://t.me"),
                InlineKeyboardButton("🎈 𝕲𝖗𝖔𝖚𝖕 🎈", url="https://t.me")
            ],
            [
                InlineKeyboardButton("✨️ ʀʊʟɛֆ ✨️", url="https://telegra.ph")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(welcome_keyboard)

        welcome_text = (
            f"Hai {user_mention}❤️,\n"
            f"Welcome To \n"
            f"★📣ഉർവശി ടീയറ്റേഴ്‌സ് ™📣★,\n\n"
            f"♻️മടിക്കേണ്ട കൂട്ടുകാർക്കും ഷെയർ ചെയ്തോ ഗ്രൂപ്പ്‌ പവർ ആകട്ടെ...\n\n"
            f"<b><u>Movie Request Format</u></b>\n\n"
            f"Bhramam ❌\n"
            f"Bhramam 2020✅\n"
            f"ഇങ്ങനെ റിക്വസ്റ്റ് ചെയ്തിട്ടും മൂവി ലഭിച്ചില്ലെങ്കിൽ \n"
            f"<code>/request Bhramam 2020</code> (ഉപ ഉപയോഗിക്കുക)\n\n"
            f"🚸 <b>NB:</b> [Movie+Year] Format -ൽ കിട്ടിയില്ലെങ്കിൽ മാത്രം താഴെയുള്ള ബട്ടണുകൾ ഉപയോഗിക്കുക 👇"
        )
        try:
            await message.reply_text(text=welcome_text, reply_markup=reply_markup, disable_web_page_preview=True)
        except:
            pass

