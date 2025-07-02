from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client.get_default_database()
urls = db.urls

urls.create_index("expires_at", expireAfterSeconds=0)
urls.create_index('_id', unique=True)
