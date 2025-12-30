#!/usr/bin/env python3
"""FFmpeg Processor Bot - A Telegram bot for video processing"""

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from dotenv import load_dotenv
from os import environ, path, makedirs

# Load environment variables
load_dotenv('config.env', override=True)

# Setup logging
log_handlers = [logging.StreamHandler()]
try:
    makedirs('logs', exist_ok=True)
    log_handlers.append(logging.FileHandler('logs/bot.log'))
except Exception:
    pass  # Continue with console logging only

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=log_handlers
)
LOGGER = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = environ.get('BOT_TOKEN', '')
API_ID = int(environ.get('API_ID', 0))
API_HASH = environ.get('API_HASH', '')
OWNER_ID = int(environ.get('OWNER_ID', 0))

# MongoDB
MONGO_URI = environ.get('MONGO_URI', '')
DATABASE_NAME = environ.get('DATABASE_NAME', 'ffmpeg_bot')

# Directories
DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', './downloads')
OUTPUT_DIR = environ.get('OUTPUT_DIR', './outputs')

# Limits
MAX_FILE_SIZE = int(environ.get('MAX_FILE_SIZE', 2000))  # MB
MAX_DURATION = int(environ.get('MAX_DURATION', 7200))  # seconds
TG_MAX_FILE_SIZE = int(environ.get('TG_MAX_FILE_SIZE', 2000))  # MB

# Google Drive
GDRIVE_ENABLED = environ.get('GDRIVE_ENABLED', 'False').lower() == 'true'
GDRIVE_CREDENTIALS = environ.get('GDRIVE_CREDENTIALS', 'credentials.json')
GDRIVE_FOLDER_ID = environ.get('GDRIVE_FOLDER_ID', '')

# FFmpeg Defaults
DEFAULT_VIDEO_CODEC = environ.get('DEFAULT_VIDEO_CODEC', 'libx264')
DEFAULT_AUDIO_CODEC = environ.get('DEFAULT_AUDIO_CODEC', 'aac')
DEFAULT_CRF = int(environ.get('DEFAULT_CRF', 23))
DEFAULT_PRESET = environ.get('DEFAULT_PRESET', 'medium')
DEFAULT_AUDIO_BITRATE = environ.get('DEFAULT_AUDIO_BITRATE', '192k')

# Authorized Users
AUTHORIZED_USERS = environ.get('AUTHORIZED_USERS', '')
if AUTHORIZED_USERS:
    AUTHORIZED_USERS = set(int(x) for x in AUTHORIZED_USERS.split(','))
else:
    AUTHORIZED_USERS = set()

# Create directories
for directory in [DOWNLOAD_DIR, OUTPUT_DIR]:
    makedirs(directory, exist_ok=True)

# User data storage (in-memory, backed by MongoDB)
user_data = {}
processing_queue = {}

# Bot client
bot = Client(
    "ffmpeg_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML,
    workers=8
)

# Database connection (will be initialized on startup)
db = None
