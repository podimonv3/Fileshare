import logging
import threading
import asyncio  
from flask import Flask
from pyrogram import Client, idle 
from info import BOT_TOKEN, API_ID, API_HASH

# 🚨 തിരുത്തിയത്: സാധാരണ ലോഗുകൾ പ്രിന്റ് ചെയ്യാതിരിക്കാൻ റൂട്ട് ലെവൽ ERROR ആക്കി മാറ്റുന്നു
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# ഫ്ലാസ്കിന്റെയും മറ്റ് ലൈബ്രറികളുടെയും അനാവശ്യ ലോഗുകൾ ഓഫ് ചെയ്യുന്നു
logging.getLogger('werkzeug').setLevel(logging.ERROR) 
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("apscheduler").setLevel(logging.ERROR)

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
    
    # പൈറോഗ്രാം ക്ലയന്റ് സ്റ്റാർട്ട് ചെയ്യുന്നു (ഇതോടെ എല്ലാ പ്ലഗിൻസും ലോഡ് ആകും)
    await app.start()

    # 🗓️ ബോട്ട് സ്റ്റാർട്ട് ആയ ശേഷം മാത്രം ഷെഡ്യൂളർ ജോബുകൾ ആഡ് ചെയ്യുന്നു
    try:
        # scheduler.py ഫയലിൽ നിന്ന് ഫങ്ക്ഷനും ഷെഡ്യൂളറും ഇമ്പോർട്ട് ചെയ്യുന്നു
        from handlers.scheduler import scheduler, send_daily_wishes 
        
        # 🚨 കൃത്യമായി 'client' ആയി നമ്മുടെ ബോട്ടിന്റെ 'app' പാസ്സ് ചെയ്യുന്നു 👇
        scheduler.add_job(send_daily_wishes, "cron", hour=7, minute=0, kwargs={"client": app, "wish_type": "morning"})
        scheduler.add_job(send_daily_wishes, "cron", hour=13, minute=0, kwargs={"client": app, "wish_type": "afternoon"})
        scheduler.add_job(send_daily_wishes, "cron", hour=18, minute=30, kwargs={"client": app, "wish_type": "evening"})
        scheduler.add_job(send_daily_wishes, "cron", hour=22, minute=0, kwargs={"client": app, "wish_type": "night"})
        
        # ഷെഡ്യൂളർ സുരക്ഷിതമായി സ്റ്റാർട്ട് ചെയ്യുന്നു
        if not scheduler.running:
            scheduler.start()
            print("Wishes Scheduler Started Successfully! ⏰")
            
    except Exception as e:
        logger.error(f"Scheduler Setup Error: {e}")
        
    # ബോട്ട് എപ്പോഴും ആക്ടീവ് ആയി നിലനിർത്താൻ (Keep-alive loop)
    await idle()
    
    # ബോട്ട് സ്റ്റോപ്പ് ചെയ്യുമ്പോൾ സുരക്ഷിതമായി ക്ലോസ് ചെയ്യാൻ
    await app.stop()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

