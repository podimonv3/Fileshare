import logging
import threading
import asyncio  
from flask import Flask
from pyrogram import Client, idle 
from info import BOT_TOKEN, API_ID, API_HASH
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 🚨 തിരുത്തിയത്: സാധാരണ ലോഗുകൾ പ്രിന്റ് ചെയ്യാതിരിക്കാൻ റൂട്ട് ലെവൽ ERROR ആക്കി മാറ്റുന്നു 👇
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# 🚨 തിരുത്തിയത്: ഫ്ലാസ്കിന്റെ വിസിറ്റ് ലോഗുകൾ Koyeb ലോഗിൽ വരാതിരിക്കാൻ ഓഫ് ചെയ്യുന്നു 👇
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# 🚨 തിരുത്തിയത്: പൈറോഗ്രാമിന്റെ പ്ലഗിൻ ലോഡിങ് ഇൻഫോ ലോഗുകൾ ഓഫ് ചെയ്യുന്നു 👇
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# 🚨 തിരുത്തിയത്: അപ്‌ഷെഡ്യൂളർ ടൈമറിന്റെ (APScheduler) ഇൻഫോ ലോഗുകൾ ഓഫ് ചെയ്യുന്നു 👇
logging.getLogger("apscheduler").setLevel(logging.ERROR)

# ⏰ ഇന്ത്യൻ സമയം അടിസ്ഥാനമാക്കി മെയിൻ ഷെഡ്യൂളർ സെറ്റ് ചെയ്യുന്നു
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

@flask_app.route('/')
def home():
    return "ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀"

def run_flask():
    import os
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# Pyrogram Client with automatic plugin loading
app = Client(
    "advanced_file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="handlers")
)

async def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        logger.error("Error: ആവശ്യമായ ടോക്കണുകൾ സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    # ഫ്ലാസ്ക് വെബ് സെർവർ പശ്ചാത്തലത്തിൽ റൺ ചെയ്യുന്നു
    threading.Thread(target=run_flask, daemon=True).start()
    
    # ലൂപ്പിനുള്ളിൽ വെച്ച് പൈറോഗ്രാം ക്ലയന്റ് സ്റ്റാർട്ട് ചെയ്യുന്നു
    await app.start()

    # 🗓️ വിഷ് ഫയലിൽ നിന്നും ഫങ്ക്ഷൻ ഇമ്പോർട്ട് ചെയ്ത് ഇവിടുത്തെ മെയിൻ ഷെഡ്യൂളറിലേക്ക് ആഡ് ചെയ്യുന്നു
    try:
        # ഇവിടെ 'handlers.wishes' എന്നതിന് പകരം നിങ്ങളുടെ wishes ഫയൽ കിടക്കുന്ന ശരിയായ പാത്ത് (Path) നൽകുക
        from handlers.wishes import send_daily_wishes 
        
        # ടൈമിംഗ് ജോബുകൾ സെറ്റ് ചെയ്യുന്നു
        scheduler.add_job(send_daily_wishes, "cron", hour=7, minute=0, args=[app, "morning"])
        scheduler.add_job(send_daily_wishes, "cron", hour=13, minute=0, args=[app, "afternoon"])
        scheduler.add_job(send_daily_wishes, "cron", hour=18, minute=30, args=[app, "evening"])
        scheduler.add_job(send_daily_wishes, "cron", hour=22, minute=0, args=[app, "night"])
    except Exception as e:
        logger.error(f"Scheduler Jobs Adding Error: {e}")
    
    # ഷെഡ്യൂളർ സുരക്ഷിതമായി സ്റ്റാർട്ട് ചെയ്യുന്നു
    if not scheduler.running:
        scheduler.start()
        
    # ബോട്ട് എപ്പോഴും ആക്ടീവ് ആയി നിലനിർത്താൻ (Keep-alive loop)
    await idle()
    
    # ബോട്ട് സ്റ്റോപ്പ് ചെയ്യുമ്പോൾ സുരക്ഷിതമായി ക്ലോസ് ചെയ്യാൻ
    await app.stop()

if __name__ == '__main__':
    # async main ഫങ്ക്ഷൻ റൺ ചെയ്യാനുള്ള ശരിയായ വഴി
    asyncio.get_event_loop().run_until_complete(main())
