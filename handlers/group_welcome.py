from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_message(filters.new_chat_members)
async def welcome_new_member(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue

        user_mention = member.mention
        
        # 🔗 ഒഫീഷ്യൽ ലിങ്കുകൾ ബട്ടണുകളാക്കി ഇവിടെ നൽകിയിരിക്കുന്നു
        welcome_keyboard = [
            [
                InlineKeyboardButton("🎈 𝕮𝖍𝖆𝖓𝖓𝖊𝖑 🎈", url="https://t.me/UrvashiTheaters_Main"),
                InlineKeyboardButton("🎈 𝕲𝖗𝖔𝖚𝖕 🎈", url="https://t.me/+eb__Eg3RS2IyZWQ1")
            ],
            [
                InlineKeyboardButton("✨️ ʀʊʟɛֆ ✨️", url="https://telegra.ph/RULES-OF-12-22")
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
            f"<code>/request Bhramam 2020</code> (ഉപയോഗിക്കുക)\n\n"
            f"🚸 <b>NB:</b> [Movie+Year] Format -ൽ കിട്ടിയില്ലെങ്കിൽ മാത്രം താഴെയുള്ള ബട്ടണുകൾ ഉപയോഗിക്കുക 👇"
        )
        
        # ⚠️ ഇവിടെ കൃത്യമായ ഫോട്ടോ ലിങ്ക് (Direct URL) നൽകുക (e.g., https://catbox.moe)
        photo_url = "https://files.catbox.moe/oryxah.jpg" 

        try:
            await message.reply_photo(
                photo=photo_url,
                caption=welcome_text, 
                reply_markup=reply_markup, 
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            print(f"Photo load ആയില്ല, പകരം text അയക്കുന്നു. Error: {e}")
            try:
                # ഫോട്ടോ ലോഡ് ആയില്ലെങ്കിൽ ടെക്സ്റ്റ് മെസ്സേജ് മാത്രമായി അയക്കുന്നു
                await message.reply_text(
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as text_err:
                print(f"Text Message Error: {text_err}")
