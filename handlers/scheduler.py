import random
import asyncio
import logging
from pyrogram import Client, enums
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import users_collection

logger = logging.getLogger(__name__)

# 📸 നാല് സമയങ്ങളിലേക്കുമുള്ള മനോഹരമായ ചിത്രങ്ങൾ
MORNING_IMAGES = [
    "https://gecdesigns.com"
]

AFTERNOON_IMAGES = [
    "https://gecdesigns.com"
]

EVENING_IMAGES = [
    "https://lifekafunda.com"
]

NIGHT_IMAGES = [
    "https://lifekafunda.com"
]

# ==========================================
# 📝 വെറൈറ്റി മലയാളം ടെക്സ്റ്റുകളുടെ ലിസ്റ്റ് 👇
# ==========================================

MORNING_TEXTS = [
    "☀️ **സുപ്രഭാതം!**\n\nനിങ്ങളുടെ ഈ ദിവസം സന്തോഷവും നന്മയും നിറഞ്ഞതായിരിക്കട്ടെ എന്ന് ആശംസിക്കുന്നു! 🌸✨ ഗ്രൂപ്പ് പവർ ആകട്ടെ!",
    "✨ **Good Morning Everyone!**\n\nഒരു പുതിയ പുലരിയിലേക്ക് സ്വാഗതം. ഒട്ടനവധി നല്ല നിമിഷങ്ങൾ ഈ ദിവസം നിങ്ങൾക്ക് സമ്മാനിക്കട്ടെ! 💫",
    "🌻 **ഒരു പുതിയ പ്രഭാതം കൂടി!**\n\nഇന്നത്തെ ദിവസം നിങ്ങളുടെ എല്ലാ ആഗ്രഹങ്ങളും സഫലമാകട്ടെ എന്ന് പ്രാർത്ഥിക്കുന്നു. ഹാപ്പി മോർണിംഗ് കൂട്ടുകാരേ! 🥰",
    "☕ **സുപ്രഭാതം സുഹൃത്തുക്കളേ...**\n\nചൂടുള്ള ഒരു കപ്പി ചായക്കൊപ്പം പോസിറ്റീവ് എനർജിയോടെ ഈ ദിവസം ആരംഭിക്കൂ! Have a beautiful day! 🌅",
    "🌈 **Good Morning!**\n\nമനസ്സിൽ എപ്പോഴും നല്ല ചിന്തകൾ മാത്രം വെച്ചുപുലർത്തുക. വിജയം നിറഞ്ഞ ഒരു നല്ല ദിവസം ആശംസിക്കുന്നു! 💫⭐"
]

AFTERNOON_TEXTS = [
    "🌤️ **ശുഭ ഉച്ചാഹ്നം! (Good Afternoon)**\n\nഎല്ലാവരും ഉച്ചഭക്ഷണമൊക്കെ കഴിച്ചോ? സുഖകരവും ഉന്മേഷഭരിതവുമായ ഒരു ഉച്ചനേരം നേരുന്നു! 🍛✨",
    "🍱 **Good Afternoon Friends!**\n\nരാവിലത്തെ ജോലികളുടെ തിരക്കൊക്കെ കഴിഞ്ഞു കാണുമല്ലോ. ഒരു ചെറിയ റെസ്റ്റ് ഒക്കെ എടുത്ത് ഉച്ചനേരം പവർ ആക്കൂ! ☕✨",
    "☀️ **ഹലോ കൂട്ടുകാരേ... Good Afternoon!**\n\nഈ മനോഹരമായ ഉച്ചസമയത്ത് നിങ്ങൾക്ക് എല്ലാവിധ നന്മകളും ഉന്മേഷവും നേരുന്നു! 💫",
    "🍚 **ശുഭ ഉച്ചാഹ്നം!**\n\nരുചികരമായ ഉച്ചഭക്ഷണത്തോടൊപ്പം സമാധാനമുള്ള ഒരു ഉച്ചസമയം ആശംസിക്കുന്നു. ഗ്രൂപ്പിൽ സജീവമാകുമല്ലോ! 🤝",
    "✨ **Have a wonderful afternoon!**\n\nപകുതി ദിവസം കഴിഞ്ഞു, ബാക്കി പകുതി ദിവസം കൂടി അടിപൊളിയാക്കാൻ എല്ലാവർക്കും സാധിക്കട്ടെ! 🌈"
]

EVENING_TEXTS = [
    "🌆 **ശുഭ സായാഹ്നം!**\n\nപകലിന്റെ തിരക്കുകളെല്ലാം ഒടുങ്ങി ശാന്തമായ ഒരു വൈകുന്നേരം ആശംസിക്കുന്നു! ❤️☕",
    "✨ **Good Evening Friends!**\n\nസുഖകരമായ ഒരു വൈകുന്നേരം നേരുന്നു. ചായ കുടിച്ചോ എല്ലാവരും? ☕🍟",
    "🌇 **ഒരു മനോഹരമായ വൈകുന്നേരം കൂടി!**\n\nമനസ്സിന് കുളിർമയേകുന്ന നല്ലൊരു സായാഹ്നം എല്ലാവർക്കും നേരുന്നു! പവർ വരട്ടെ! 💫",
    "☕ **ശുഭ സായാഹ്നം കൂട്ടുകാരേ...**\n\nതിരക്കുകളിൽ നിന്നെല്ലാം മാറി കുടുംബത്തോടൊപ്പം സന്തോഷത്തോടെ ചെലവഴിക്കാൻ നല്ലൊരു വൈകുന്നേരം ആശംസിക്കുന്നു! 🥰",
    "🍃 **Good Evening!**\n\nതണുത്ത കാറ്റും ചൂടുള്ള ചായയുമായി ഈ വൈകുന്നേരം നമുക്ക് അടിപൊളിയാക്കാം! 🍩☕"
]

NIGHT_TEXTS = [
    "🌙 **ശുഭരാത്രി! (Good Night)**\n\nമധുരമുള്ള സ്വപ്നങ്ങളുമായി ശാന്തമായി ഉറങ്ങൂ. നാളെ ഒരു പുതിയ നല്ല ദിവസത്തിനായി കാത്തിരിക്കാം! 😴⭐",
    "✨ **Good Night Everyone!**\n\nഇന്നത്തെ ദിവസത്തെ നല്ല ഓർമ്മകളോടെ മനസ്സ് നിറച്ച് എല്ലാവരും സുഖമായി ഉറങ്ങുക. ശുഭരാത്രി! 🌌",
    "🌟 **ശുഭരാത്രി നേരുന്നു!**\n\nനല്ല സ്വപ്നങ്ങളും സമാധാനമുള്ള ഉറക്കവും നിങ്ങൾക്ക് ഉണ്ടാകട്ടെ. നാളെ രാവിലെ കാണാം! ടേക്ക് കെയർ 💤",
    "🌛 **Good Night Friends...**\n\nഫോണൊക്കെ മാറ്റിവെച്ച് ഉറങ്ങാൻ സമയമായി കേട്ടോ! എല്ലാവർക്കും സുഖകരമായ നിദ്ര ആശംസിക്കുന്നു! 😴",
    "💤 **മധുരമായ സ്വപ്നങ്ങളിലേക്ക്...**\n\nക്ഷീണമകറ്റി നാളത്തെ പ്രഭാതത്തിലേക്ക് ഉന്മേഷത്തോടെ ഉണരാൻ നല്ലൊരു ഉറക്കം ആശംസിക്കുന്നു. ശുഭരാത്രി! 🌙⭐"
]


async def send_daily_wishes(client: Client, wish_type: str):
    """എല്ലാ ഗ്രൂപ്പുകളിലേക്കും യൂസർമാരിലേക്കും വിഷ് മെസ്സേജുകൾ അയക്കുന്ന മെയിൻ ഫങ്ക്ഷൻ"""
    logger.info(f"Starting {wish_type} wish broadcast loop...")
    
    # ഓരോ ലിസ്റ്റിൽ നിന്നും ഒരു ടെക്സ്റ്റും ഇമേജും റാൻഡം ആയി തിരഞ്ഞെടുക്കുന്നു
    if wish_type == "morning":
        image = random.choice(MORNING_IMAGES)
        text = random.choice(MORNING_TEXTS)
    elif wish_type == "afternoon":
        image = random.choice(AFTERNOON_IMAGES)
        text = random.choice(AFTERNOON_TEXTS)
    elif wish_type == "evening":
        image = random.choice(EVENING_IMAGES)
        text = random.choice(EVENING_TEXTS)
    else: # night
        image = random.choice(NIGHT_IMAGES)
        text = random.choice(NIGHT_TEXTS)

    # ഡാറ്റാബേസിൽ ഉള്ള എല്ലാ ഐഡികളും എടുക്കുന്നു
    all_targets = users_collection.find()
    
    for target in all_targets:
        chat_id = target['_id']
        try:
            # 1️⃣ ആദ്യം ചിത്രം സഹിതം അയക്കാൻ ശ്രമിക്കുന്നു 📸
            await client.send_photo(
                chat_id=chat_id,
                photo=image,
                caption=text,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as photo_error:
            # 🚨 ചിത്രം ലോഡ് ആയില്ലെങ്കിൽ വെറും ടെക്സ്റ്റ് മെസ്സേജ് ആയി അയക്കുന്നു 📝
            logger.warning(f"ചിത്രം അയക്കാൻ പറ്റിയില്ല, വെറും ടെക്സ്റ്റ് അയക്കുന്നു: {photo_error}")
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception as msg_error:
                logger.error(f"Target {chat_id}-ലേക്ക് ടെക്സ്റ്റും അയക്കാൻ കഴിഞ്ഞില്ല: {msg_error}")
                continue
        
        # ⏱️ ടെലഗ്രാം ഫ്ലഡ് ലിമിറ്റ് എറർ വരാതിരിക്കാൻ ചെറിയ ഗ്യാപ്പ്
        await asyncio.sleep(0.1)

# ⏰ ടൈമർ ഷെഡ്യൂളർ സെറ്റ് ചെയ്യുന്നു (ഇന്ത്യൻ സമയം IST അടിസ്ഥാനമാക്കി)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

from bot import app 

# 🗓️ ദിവസേന കൃത്യസമയത്ത് മെസ്സേജ് പോകാനുള്ള ടൈമിംഗ് ലിസ്റ്റ്
# 1. രാവിലെ 07:00 മണിക്ക് (Good Morning)
scheduler.add_job(send_daily_wishes, "cron", hour=7, minute=0, args=[app, "morning"])

# 2. ഉച്ചയ്ക്ക് 01:00 മണിക്ക് (Good Afternoon)
scheduler.add_job(send_daily_wishes, "cron", hour=13, minute=0, args=[app, "afternoon"])

# 3. വൈകുന്നേരം 06:30 മണിക്ക് (Good Evening)
scheduler.add_job(send_daily_wishes, "cron", hour=18, minute=30, args=[app, "evening"])

# 4. രാത്രി 10:00 മണിക്ക് (Good Night)
scheduler.add_job(send_daily_wishes, "cron", hour=22, minute=0, args=[app, "night"])

# ഷെഡ്യൂളർ ആരംഭിക്കുന്നു
scheduler.start()
