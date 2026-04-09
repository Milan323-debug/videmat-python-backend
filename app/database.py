from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ytdownloader")

client = AsyncIOMotorClient(MONGODB_URI)
db = client.get_default_database()

# Collections
history_collection = db["history"]
videocache_collection = db["videocache"]

async def connect_db():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise

async def close_db():
    client.close()
    print("🔌 MongoDB connection closed")
