#!/usr/bin/env python3
"""MongoDB Database Handler"""

from motor.motor_asyncio import AsyncIOMotorClient
import logging

LOGGER = logging.getLogger(__name__)

class Database:
    def __init__(self, uri: str, database_name: str):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[database_name]
        self._users = self._db.users
        self._settings = self._db.settings
        
    async def connect(self):
        """Test the database connection"""
        await self._client.admin.command('ping')
        LOGGER.info("Database connection established")
        
    async def get_user(self, user_id: int) -> dict:
        """Get user data from database"""
        user = await self._users.find_one({"_id": user_id})
        return user or {}
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add a new user or update existing"""
        await self._users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                },
                "$setOnInsert": {
                    "settings": self.default_settings()
                }
            },
            upsert=True
        )
        
    async def update_user_settings(self, user_id: int, settings: dict):
        """Update user settings"""
        await self._users.update_one(
            {"_id": user_id},
            {"$set": {"settings": settings}}
        )
        
    async def get_user_settings(self, user_id: int) -> dict:
        """Get user settings"""
        user = await self.get_user(user_id)
        return user.get("settings", self.default_settings())
    
    async def get_all_users(self) -> list:
        """Get all users"""
        users = []
        async for user in self._users.find():
            users.append(user)
        return users
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        return await self._users.count_documents({})
    
    @staticmethod
    def default_settings() -> dict:
        """Default user settings"""
        return {
            # Video Settings
            "video_codec": "libx264",
            "audio_codec": "aac",
            "crf": 23,
            "preset": "medium",
            "resolution": None,
            
            # Output Settings
            "keep_source": False,
            "custom_filename": None,
            "output_format": None,
            
            # Watermark
            "watermark_enabled": False,
            "watermark_text": None,
            "watermark_position": "bottom_right",
            
            # Metadata
            "metadata_title": None,
            "metadata_author": None,
            
            # Processing state
            "current_operation": None,
            "processing_file": None,
        }


# Global database instance
db_instance: Database = None

async def init_database(uri: str, database_name: str) -> Database:
    """Initialize database connection"""
    global db_instance
    db_instance = Database(uri, database_name)
    await db_instance.connect()
    return db_instance

def get_db() -> Database:
    """Get database instance"""
    return db_instance
