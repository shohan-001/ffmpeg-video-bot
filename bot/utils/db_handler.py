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
        
    async def delete_user(self, user_id: int):
        """Delete user from database"""
        await self._users.delete_one({"_id": user_id})
        
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
            "video_codec": "libx264", # H264
            "audio_codec": "aac",
            "crf": 26, # Default 26 in ref bot
            "preset": "medium",
            "resolution": "OG", # OG = Original
            "reframe": None, # 4, 8, 16
            "tune": None, # animation
            "cabac": True, # bool
            "bits": None, # 10 bit
            "frame": None, # fps
            "aspect": None, # 16:9
            "hevc": False, # x265

            # Audio Settings
            "audio_bitrate": None, # 192, etc
            "sample_rate": None, # 48K
            "channels": None, # 2.0, 5.1

            # Subtitle Settings
            "hardsub": False,
            "subtitles": True, # Softsub

            # Output Settings
            "keep_source": False,
            "custom_filename": None,
            "output_format": "MKV", # Default MKV
            
            # Watermark
            "watermark_enabled": False,
            "watermark_text": None,
            "watermark_position": "bottom_right",
            
            # Metadata
            "metadata_title": None,
            "metadata_author": None,
            "metadata_w": False, # Watermark metadata
            
            # Processing state
            "current_operation": None,
            "processing_file": None,
        }



    async def update_setting(self, user_id: int, key: str, value: any):
        """Update a specific setting"""
        await self._users.update_one(
            {"_id": user_id},
            {"$set": {f"settings.{key}": value}}
        )

    # Helper methods for specific settings (mimicking reference bot style)
    async def get_hevc(self, user_id): return (await self.get_user_settings(user_id)).get('hevc')
    async def set_hevc(self, user_id, value): await self.update_setting(user_id, 'hevc', value)
    
    async def get_resolution(self, user_id): return (await self.get_user_settings(user_id)).get('resolution')
    async def set_resolution(self, user_id, value): await self.update_setting(user_id, 'resolution', value)
    
    async def get_preset(self, user_id): return (await self.get_user_settings(user_id)).get('preset')
    async def set_preset(self, user_id, value): await self.update_setting(user_id, 'preset', value)
    
    async def get_audio(self, user_id): return (await self.get_user_settings(user_id)).get('audio_codec')
    async def set_audio(self, user_id, value): await self.update_setting(user_id, 'audio_codec', value)
    
    async def get_crf(self, user_id): return (await self.get_user_settings(user_id)).get('crf')
    async def set_crf(self, user_id, value): await self.update_setting(user_id, 'crf', value)

    async def get_extensions(self, user_id): return (await self.get_user_settings(user_id)).get('output_format')
    async def set_extensions(self, user_id, value): await self.update_setting(user_id, 'output_format', value)

    async def get_watermark(self, user_id): return (await self.get_user_settings(user_id)).get('watermark_enabled')
    async def get_metadata_w(self, user_id): return (await self.get_user_settings(user_id)).get('metadata_w')
    
    async def get_hardsub(self, user_id): return (await self.get_user_settings(user_id)).get('hardsub')
    async def get_subtitles(self, user_id): return (await self.get_user_settings(user_id)).get('subtitles')
    
    async def get_reframe(self, user_id): return (await self.get_user_settings(user_id)).get('reframe')
    async def get_frame(self, user_id): return (await self.get_user_settings(user_id)).get('frame')
    async def get_tune(self, user_id): return (await self.get_user_settings(user_id)).get('tune')
    async def get_bits(self, user_id): return (await self.get_user_settings(user_id)).get('bits')
    async def get_cabac(self, user_id): return (await self.get_user_settings(user_id)).get('cabac')
    async def get_aspect(self, user_id): return (await self.get_user_settings(user_id)).get('aspect')
    
    async def get_samplerate(self, user_id): return (await self.get_user_settings(user_id)).get('sample_rate')
    async def get_bitrate(self, user_id): return (await self.get_user_settings(user_id)).get('audio_bitrate')
    async def get_channels(self, user_id): return (await self.get_user_settings(user_id)).get('channels')

    # Thumbnail
    async def get_thumbnail(self, user_id):
        user = await self.get_user(user_id)
        return user.get('thumbnail')

    async def set_thumbnail(self, user_id, file_id):
        await self._users.update_one(
            {"_id": user_id},
            {"$set": {"thumbnail": file_id}}
        )

# Global database instance
db_instance: Database = None

async def init_database(uri: str, database_name: str) -> Database:
    """Initialize database connection"""
    global db_instance
    db_instance = Database(uri, database_name)
    await db_instance.connect()
    return db_instance

    # Log Channel (Global Setting or Per User?)
    # Reference bot has a global log channel defined in config, but maybe we can store per-user logs?
    # For now, let's keep it simple as per reference bot (Config based usually, but here we can add if needed)
    # Actually, reference bot often uses a LOG_CHANNEL var.
    # We will assume LOG_CHANNEL is in config.env, but if we want to store *last* log, we can.
    # Let's just stick to thumbnail for DB.

def get_db() -> Database:
    """Get database instance"""
    return db_instance
