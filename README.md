# FFmpeg Processor Bot V2.1.0 🚀

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

A powerful Telegram bot for video processing using FFmpeg. Deploy on your VPS or Heroku for full control over video manipulation.

## Features

### 🎬 Video Operations
| Feature | Description |
|---------|-------------|
| **FFMPEG CMD** | Run custom FFmpeg commands |
| **MegaMetaData** | Edit video metadata |
| **Vid+Vid** | Merge/concatenate videos |
| **Vid+Aud** | Add or replace audio track |
| **Vid+Sub** | Add subtitle track |
| **StreamSwap** | Reorder streams |
| **Extract** | Extract video/audio/subtitles |
| **Remove** | Remove specific streams |
| **Encode** | Re-encode with quality settings |
| **Convert** | Change format (mp4, mkv, webm, gif, etc.) |
| **Watermark** | Add image/text watermark |
| **Sub Intro** | Add text intro to video |
| **Hardsub** | Burn subtitles into video |
| **Trim** | Cut video segments |

### ⚡ Extra Features
- **Real-time Progress Tracking**: Detailed list-style progress bars for all operations
- **Clean UI**: Minimalist, emoji-free interface for better readability
- Video speed change (0.25x - 4x)
- Video rotation and flip
- Resolution change
- Video compression
- Screenshot extraction
- Thumbnail extraction
- Audio extraction (MP3, AAC, FLAC, etc.)
- **Google Drive upload** (for files >2GB)

### 🆕 New in v2.1.0
| Feature | Description |
|---------|-------------|
| **YT-DLP Support** | Download from YouTube, Vimeo, Twitter, and 1000+ sites |
| **Encoding Profiles** | Quick presets: High Quality, Balanced, Small Size |
| **Task Queuing** | Queue multiple tasks per user (configurable limit) |
| **Authorized Groups** | Restrict bot to specific Telegram groups |
| **Persistent Settings** | User preferences saved to MongoDB |
| **Upload Preferences** | Toggle default upload destination (Telegram/GDrive) |

## Requirements

- VPS with 1+ CPU cores, 2GB+ RAM
- Docker and Docker Compose
- Telegram Bot Token
- Google Service Account (optional, for GDrive upload)

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/ffmpeg-processor-bot.git
cd ffmpeg-processor-bot
```

### 2. Configure the bot
```bash
cp config.env.sample config.env
nano config.env
```

Edit `config.env` with your credentials:
```env
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_id
API_ID=your_api_id
API_HASH=your_api_hash
MONGO_URI=mongodb://mongodb:27017

# Limits
MAX_FILE_SIZE=2000
TG_MAX_FILE_SIZE=2000
MAX_DURATION=7200

# Google Drive (optional)
GDRIVE_ENABLED=True
GDRIVE_CREDENTIALS=credentials.json
GDRIVE_FOLDER_ID=your_folder_id
```

### 3. Google Drive Setup (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Google Drive API
4. Create a Service Account and download `credentials.json`
5. Place `credentials.json` in the bot directory
6. Share your destination folder with the service account email

### 4. Deploy with Docker
```bash
docker-compose up -d --build
```

### 5. View logs
```bash
docker-compose logs -f ffmpeg-bot
```

## Manual Installation (without Docker)

### Install dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3-pip ffmpeg mediainfo

# Install Python packages
pip3 install -r requirements.txt
```

### Run the bot
```bash
python3 -m bot
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Telegram Bot Token from @BotFather |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash from my.telegram.org |
| `MONGO_URI` | ❌ | MongoDB connection string |
| `AUTHORIZED_USERS` | ❌ | Comma-separated user IDs (empty = public) |
| `AUTHORIZED_GROUPS` | ❌ | Comma-separated group IDs (empty = all groups) |
| `ENABLE_YTDLP` | ❌ | Enable YT-DLP for video platforms (True/False) |
| `MAX_QUEUE_PER_USER` | ❌ | Max pending tasks per user (default: 3) |
| `LOG_CHANNEL` | ❌ | Channel ID to forward processed files (0 = off) |
| `MAX_FILE_SIZE` | ❌ | Maximum download size in MB (default: 2000) |
| `TG_MAX_FILE_SIZE` | ❌ | Max file size for TG upload (default: 2000) |
| `MAX_DURATION` | ❌ | Max video duration in seconds (default: 7200) |
| `DEFAULT_AUDIO_BITRATE`| ❌ | Audio bitrate for encoding (default: 192k) |
| `GDRIVE_ENABLED` | ❌ | Enable Google Drive upload (True/False) |
| `GDRIVE_CREDENTIALS` | ❌ | Path to credentials.json |
| `GDRIVE_FOLDER_ID` | ❌ | Google Drive folder ID for uploads |

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help message |
| `/settings` | View your settings |
| `/vset` | View detailed encode settings |
| `/thumb` | View/Set custom thumbnail |
| `/reset` | Reset user settings |
| `/queue` | View active tasks list |
| `/status` | View system status |
| `/dl` | Reply to file/video to process |
| `/zip` | Archive file/video |
| `/unzip` | Extract archive |
| `/cancel` | Cancel current operation |

### Admin Commands (Owner Only)
| Command | Description |
|---------|-------------|
| `/authgrp` | Authorize groups (run in group to toggle) |
| `/cookies` | Manage YT-DLP cookies (upload cookies.txt) |
| `/gdrive` | Manage GDrive credentials (upload credentials.json) |
| `/stats` | Bot statistics |
| `/broadcast` | Broadcast message to all users |
| `/update` | Update bot from GitHub (auto-restart) |
| `/restart` | Restart the bot |
| `/log` | View bot logs |
| `/shell` | Run shell commands |
| `/clean` | Clean cache folders |
| `/speedtest` | Run server speedtest |

## Setup Guides

### YouTube Cookie Setup (for age-restricted/private videos)
1. Install **"Get cookies.txt LOCALLY"** Chrome extension
2. Go to YouTube and **login** to your account
3. Click extension icon → **Export** cookies.txt
4. Send `/cookies set` in bot → Upload the file
5. YouTube downloads should now work!

### Google Drive Upload Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Drive API**
3. Create **Service Account** → Download credentials.json
4. Send `/gdrive set` in bot → Upload credentials.json
5. **Share** your GDrive folder with the service account email
6. Set `GDRIVE_FOLDER_ID` in config.env

### Group Authorization
Run `/authgrp` in any group to authorize/de-authorize it.
- Running in group toggles authorization
- `/authgrp` in private shows authorized groups list
- `/authgrp add <ID>` or `/authgrp remove <ID>` to manage manually

## Usage

1. Send a video file to the bot
2. Select an operation from the menu
3. Follow the prompts
4. Receive your processed video!

### Multi-Video Merge
1. Click **Vid+Vid** in the menu
2. Send multiple videos or YouTube URLs
3. Click **Done - Start Merge** when finished
4. Videos will be merged in order

## Support

Join our Telegram channel for updates and support.

## License

MIT License - See LICENSE file for details.

