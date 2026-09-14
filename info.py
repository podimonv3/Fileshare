import os

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")
BOT_TOKEN = os.getenv("BOT_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URI", None)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003851866517"))

# ----------------- CHANNEL CONFIGURATION -----------------
# ഫയലുകൾ വരുന്ന നിങ്ങളുടെ പ്രധാന ചാനലിന്റെ ID (Source Channel)
SOURCE_CHANNEL_ID = int(os.environ.get("SOURCE_CHANNEL_ID", -1003820034767))

# ഫയലുകൾ പോകേണ്ട രണ്ടാമത്തെ ചാനലിന്റെ ID (Target Channel)
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID", -1003932459936))
# ---------------------------------------------------------

# നിങ്ങളുടെ ബോട്ടിന്റെ മറ്റ് സെറ്റിങ്സുകൾ (Token, API ID മുതലായവ) ഇതിന് താഴെ വരാം...

