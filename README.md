# FFmpeg Processor Bot

A powerful Telegram bot for video processing using FFmpeg. Deploy on your VPS for full control over video manipulation.

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
- Video speed change (0.25x - 4x)
- Video rotation and flip
- Resolution change
- Video compression
- Screenshot extraction
- Thumbnail extraction
- Audio extraction (MP3, AAC, FLAC, etc.)
- **Google Drive upload** (for files >2GB)

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
| `MAX_FILE_SIZE` | ❌ | Maximum file size in MB (default: 2000) |
| `GDRIVE_ENABLED` | ❌ | Enable Google Drive upload (True/False) |
| `GDRIVE_CREDENTIALS` | ❌ | Path to credentials.json |
| `GDRIVE_FOLDER_ID` | ❌ | Google Drive folder ID for uploads |

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help message |
| `/settings` | View your settings |
| `/ping` | Check bot latency |
| `/stats` | Bot statistics (owner only) |
| `/broadcast` | Broadcast message (owner only) |

## Usage

1. Send a video file to the bot
2. Select an operation from the menu
3. Follow the prompts
4. Receive your processed video!

## Support

Join our Telegram channel for updates and support.

## License

MIT License - See LICENSE file for details.
