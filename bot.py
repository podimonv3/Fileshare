import logging
import threading
from flask import Flask
from pyrogram import Client
from info import BOT_TOKEN, API_ID, API_HASH
# 🚨 തിരുത്തിയത്: ഇവിടെ AsyncIOScheduler ഇമ്പോർട്ട് ചെയ്തു
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# 🚨 തിരുത്തിയത്: ശരിയായ ഷെഡ്യൂളർ ഒബ്ജക്റ്റ് ക്രിയേറ്റ് ചെയ്തു
scheduler = AsyncIOScheduler()

@flask_app.route('/')
def home():
    return "ബോട്ട് വിജയകരമായി റൺ ആകുന്നു... 🚀"

def run_flask():
    import os
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# Pyrogram Client with automatic plugin loading
app = Client(
    "advanced_file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="handlers") # automatically loads all files inside handlers/
)

def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        logger.error("Error: ആവശ്യമായ ടോക്കണുകൾ സെറ്റ് ചെയ്തിട്ടില്ല!")
        return

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("ബോട്ട് വിജയകരമായി റൺ ആകുന്നു...")
    
    # 🚨 തിരുത്തിയത്: ബോട്ട് റൺ ആകുന്നതിനൊപ്പം ബാക്ക്ഗ്രൗണ്ട് ടൈമറും സ്റ്റാർട്ട് ചെയ്യുന്നു
    if not scheduler.running:
        scheduler.start()
        
    app.run()

if __name__ == '__main__':
    main()

