from pymongo import MongoClient

uri = "mongodb+srv://krid_db_user:3T60F6j1H5XXKhHV@cluster0.fwz33kl.mongodb.net/?appName=Cluster0"

client = MongoClient(uri)

try:
    client.admin.command("ping")
    print("✅ Connected successfully!")
except Exception as e:
    print("❌ Connection failed:")
    print(e)