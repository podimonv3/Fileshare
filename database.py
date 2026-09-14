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

# --- Add this to the bottom of database.py ---

def is_maintenance_mode():
    """Checks if maintenance mode is enabled."""
    config = settings_collection.find_one({'_id': 'maintenance_config'})
    if config:
        return config.get('status', False)
    return False

def set_maintenance_mode(status: bool):
    """Enables (True) or Disables (False) maintenance mode."""
    settings_collection.update_one(
        {'_id': 'maintenance_config'}, 
        {'$set': {'status': status}}, 
        upsert=True
    )

# database.py-ൽ താഴെ ചേർക്കുക:
def get_delete_time():
    config = settings_collection.find_one({'_id': 'delete_config'})
    return config.get('time', 300) if config else 300

def set_delete_time(seconds: int):
    settings_collection.update_one({'_id': 'delete_config'}, {'$set': {'time': seconds}}, upsert=True)


# --- database.py-ന്റെ ഏറ്റവും താഴെ ചേർക്കുക ---

def is_protect_content():
    """പ്രൊട്ടക്ട് കണ്ടെന്റ് ഓൺ ആണോ എന്ന് നോക്കുന്നു (Default: True)"""
    config = settings_collection.find_one({'_id': 'protect_config'})
    if config:
        return config.get('status', True)
    return True

def set_protect_content(status: bool):
    """പ്രൊട്ടക്ട് കണ്ടെന്റ് ഓൺ/ഓഫ് ചെയ്യാൻ"""
    settings_collection.update_one(
        {'_id': 'protect_config'}, 
        {'$set': {'status': status}}, 
        upsert=True
    )
