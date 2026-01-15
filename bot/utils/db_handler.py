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
            # Upload preferences
            "default_destination": "telegram",  # or 'gdrive'
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

    async def get_default_destination(self, user_id): return (await self.get_user_settings(user_id)).get('default_destination', 'telegram')
    async def set_default_destination(self, user_id, value): await self.update_setting(user_id, 'default_destination', value)

    # Thumbnail
    async def get_thumbnail(self, user_id):
        user = await self.get_user(user_id)
        return user.get('thumbnail')

    async def set_thumbnail(self, user_id, file_id):
        await self._users.update_one(
            {"_id": user_id},
            {"$set": {"thumbnail": file_id}}
        )

    # ─────────────────────────────────────────────────────────────
    # Cookies Storage (for yt-dlp)
    # ─────────────────────────────────────────────────────────────
    async def get_cookies(self, user_id: int = 0) -> str:
        """Get cookies data. user_id=0 for global cookies."""
        doc = await self._settings.find_one({"_id": f"cookies_{user_id}"})
        return doc.get("data") if doc else None

    async def set_cookies(self, cookies_data: str, user_id: int = 0):
        """Store cookies data. user_id=0 for global cookies."""
        await self._settings.update_one(
            {"_id": f"cookies_{user_id}"},
            {"$set": {"data": cookies_data}},
            upsert=True
        )

    async def delete_cookies(self, user_id: int = 0):
        """Delete cookies. user_id=0 for global cookies."""
        await self._settings.delete_one({"_id": f"cookies_{user_id}"})

    async def has_cookies(self, user_id: int = 0) -> bool:
        """Check if cookies exist."""
        doc = await self._settings.find_one({"_id": f"cookies_{user_id}"})
        return doc is not None

    # ─────────────────────────────────────────────────────────────
    # Google Drive Credentials Storage
    # ─────────────────────────────────────────────────────────────
    async def get_gdrive_credentials(self) -> str:
        """Get GDrive credentials JSON string."""
        doc = await self._settings.find_one({"_id": "gdrive_credentials"})
        return doc.get("data") if doc else None

    async def set_gdrive_credentials(self, credentials_json: str):
        """Store GDrive credentials JSON string."""
        await self._settings.update_one(
            {"_id": "gdrive_credentials"},
            {"$set": {"data": credentials_json}},
            upsert=True
        )

    async def delete_gdrive_credentials(self):
        """Delete GDrive credentials."""
        await self._settings.delete_one({"_id": "gdrive_credentials"})

    async def has_gdrive_credentials(self) -> bool:
        """Check if GDrive credentials exist."""
        doc = await self._settings.find_one({"_id": "gdrive_credentials"})
        return doc is not None

    # ─────────────────────────────────────────────────────────────
    # Bot Config Storage (for dynamic settings)
    # ─────────────────────────────────────────────────────────────
    async def get_bot_config(self, key: str, default=None):
        """Get a bot config value."""
        doc = await self._settings.find_one({"_id": f"config_{key}"})
        return doc.get("value", default) if doc else default

    async def set_bot_config(self, key: str, value):
        """Set a bot config value."""
        await self._settings.update_one(
            {"_id": f"config_{key}"},
            {"$set": {"value": value}},
            upsert=True
        )

    # ─────────────────────────────────────────────────────────────
    # Authorized Groups Management
    # ─────────────────────────────────────────────────────────────
    async def get_authorized_groups(self) -> list:
        """Get list of authorized group IDs."""
        doc = await self._settings.find_one({"_id": "authorized_groups"})
        return doc.get("groups", []) if doc else []

    async def add_authorized_group(self, group_id: int) -> bool:
        """Add a group to authorized list. Returns True if added."""
        groups = await self.get_authorized_groups()
        if group_id in groups:
            return False
        groups.append(group_id)
        await self._settings.update_one(
            {"_id": "authorized_groups"},
            {"$set": {"groups": groups}},
            upsert=True
        )
        return True

    async def remove_authorized_group(self, group_id: int) -> bool:
        """Remove a group from authorized list. Returns True if removed."""
        groups = await self.get_authorized_groups()
        if group_id not in groups:
            return False
        groups.remove(group_id)
        await self._settings.update_one(
            {"_id": "authorized_groups"},
            {"$set": {"groups": groups}},
            upsert=True
        )
        return True

    async def is_group_authorized(self, group_id: int) -> bool:
        """Check if a group is authorized."""
        groups = await self.get_authorized_groups()
        return group_id in groups


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
