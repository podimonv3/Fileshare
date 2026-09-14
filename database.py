import logging
from pymongo import MongoClient
from info import MONGO_URI

logger = logging.getLogger(__name__)

try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_advanced_bot']
    batch_collection = db['batches']
    requests_collection = db['join_requests']
    settings_collection = db['settings']
    users_collection = db['users']
    logger.info("✅ MongoDB-യുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    logger.error(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")

def get_req_channel():
    config = settings_collection.find_one({'_id': 'fsub_config'})
    return config.get('channel_id', 0) if config else 0

def add_user(user_id):
    users_collection.update_one({'_id': user_id}, {'$set': {'_id': user_id}}, upsert=True)

def get_db_size():
    try:
        stats = db.command("dbstats")
        data_size_mb = stats.get('dataSize', 0) / (1024 * 1024)
        return round(data_size_mb, 2)
    except Exception as e:
        logger.error(f"Error getting DB stats: {e}")
        return 0.0

