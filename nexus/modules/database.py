from databases import Database
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the database instance
database = Database(DATABASE_URL)

async def connect_to_db():
    await database.connect()

async def disconnect_from_db():
    await database.disconnect()
