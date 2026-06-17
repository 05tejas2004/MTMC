import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv('MONGO_URI')
print(f"URI: {mongo_uri}")

if mongo_uri:
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✅ Database Connected!")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ MONGO_URI not found in .env")