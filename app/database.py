
import os

from pymongo import MongoClient
from dotenv import load_dotenv


# LOAD ENVIRONMENT VARIABLES
load_dotenv()


# MONGODB CONFIGURATION
MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "thumbai"
)


# MONGODB CONNECTION
if not MONGODB_URI:
    raise ValueError("MONGODB_URI is missing in .env")


client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000
)


# DATABASE
db = client[MONGODB_DATABASE]


# COLLECTIONS
users_collection = db["users"]

thumbnails_collection = db["thumbnails"]


# TEST DATABASE CONNECTION
def check_database_connection():

    try:

        client.admin.command("ping")

        print("MongoDB connected successfully.")

        return True

    except Exception as e:

        print("MongoDB connection failed:", str(e))

        return False
