import logging
import threading
import asyncio  
from flask import Flask
from pyrogram import Client, idle 
from info import BOT_TOKEN, API_ID, API_HASH
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# 🚨 തിരുത്തിയത്: ഫ്ലാസ്കിന്റെ അനാവശ്യ വിസിറ്റ് ലോഗുകൾ (GET / HTTP/1.1 200) Koyeb ലോഗിൽ വരാതിരിക്കാൻ ഓഫ് ചെയ്യുന്നു 👇
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) # ഗുരുതരമായ എററുകൾ അല്ലാത്ത സാധാരണ ലോഗുകൾ പ്രിന്റ് ചെയ്യില്ല

scheduler = AsyncIOScheduler()

@flask_app.route('/')
def home():
    return "ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀"

def run_flask():
    import os
    port = int(os.getenv("PORT", 8080))
    # 🚨 തിരുത്തിയത്: സുരക്ഷിതമായ റണ്ണിങ്ങിനായി debug=False എന്ന് ഉറപ്പാക്കി
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
    
    logger.info("ബോട്ട് ആരംഭിക്കുന്നു...")
    
    # അസിൻക്രണസ് ലൂപ്പിനുള്ളിൽ വെച്ച് പൈറോഗ്രാം ക്ലയന്റ് സ്റ്റാർട്ട് ചെയ്യുന്നു
    await app.start()
    logger.info("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀")
    
    # ലൂപ്പ് സജീവമായതിനാൽ ഷെഡ്യൂളർ സുരക്ഷിതമായി സ്റ്റാർട്ട് ചെയ്യുന്നു
    if not scheduler.running:
        scheduler.start()
        logger.info("ബാക്ക്ഗ്രൗണ്ട് വിഷ് ഷെഡ്യൂളർ ആരംഭിച്ചിരിക്കുന്നു! ⏰")
        
    # ബോട്ട് എപ്പോഴും ആക്ടീവ് ആയി നിലനിർത്താൻ (Keep-alive loop)
    await idle()
    
    # ബോട്ട് സ്റ്റോപ്പ് ചെയ്യുമ്പോൾ സുരക്ഷിതമായി ക്ലോസ് ചെയ്യാൻ
    await app.stop()

if __name__ == '__main__':
    # async main ഫങ്ക്ഷൻ റൺ ചെയ്യാനുള്ള ശരിയായ വഴി
    asyncio.get_event_loop().run_until_complete(main())
