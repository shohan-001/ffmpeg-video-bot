#!/usr/bin/env python3
"""Command handlers for the bot"""

from pyrogram import Client, filters
from pyrogram.types import Message
import psutil
import subprocess
import sys
import os
from time import time

from bot import bot, OWNER_ID, AUTHORIZED_USERS, LOGGER, user_data
from bot.keyboards.menus import close_button
from bot.utils.db_handler import get_db


# Helper function to check authorization
def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot"""
    if not AUTHORIZED_USERS:
        return True  # Public bot
    return user_id in AUTHORIZED_USERS or user_id == OWNER_ID


@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text(
            "❌ You are not authorized to use this bot.\n"
            "Contact the bot owner for access."
        )
        return
    
    # Add user to database
    db = get_db()
    if db:
        await db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"<b>👋 Hello {user.mention}!</b>\n\n"
        "<b>🎬 FFmpeg Processor Bot</b>\n\n"
        "I can help you process videos with FFmpeg!\n\n"
        "<b>📋 What I can do:</b>\n"
        "• <code>Merge videos (Vid+Vid)</code>\n"
        "• <code>Add audio/subtitles</code>\n"
        "• <code>Extract streams</code>\n"
        "• <code>Encode/Convert videos</code>\n"
        "• <code>Add watermarks</code>\n"
        "• <code>Burn subtitles (Hardsub)</code>\n"
        "• <code>Trim/Cut videos</code>\n"
        "• <code>Edit metadata</code>\n"
        "• <code>And much more!</code>\n\n"
        "<b>📤 Send me a video to get started!</b>\n\n"
        "Use /help for detailed commands."
    )
    
    await message.reply_text(welcome_text, reply_markup=close_button(user.id))


@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    user = message.from_user
    
    if not is_authorized(user.id):
        return
    
    help_text = (
        "<b>📖 FFmpeg Bot - Help Guide</b>\n\n"
        "<b>🔹 Basic Usage:</b>\n"
        "Just send me a video file and I'll show you the processing menu.\n\n"
        "<b>🔹 Available Operations:</b>\n\n"
        "<b>📁 Merge Operations:</b>\n"
        "• <b>Vid+Vid</b> - Merge two videos\n"
        "• <b>Vid+Aud</b> - Add audio track\n"
        "• <b>Vid+Sub</b> - Add subtitle track\n"
        "• <b>StreamSwap</b> - Reorder streams\n\n"
        "<b>📤 Extract Operations:</b>\n"
        "• <b>Extract</b> - Extract video/audio/subs\n"
        "• <b>Remove</b> - Remove specific streams\n\n"
        "<b>⚙️ Encoding:</b>\n"
        "• <b>Encode</b> - Re-encode with quality settings\n"
        "• <b>Convert</b> - Change container format\n"
        "• <b>Compress</b> - Reduce file size\n\n"
        "<b>🎨 Effects:</b>\n"
        "• <b>Watermark</b> - Add image/text watermark\n"
        "• <b>Hardsub</b> - Burn subtitles\n"
        "• <b>Sub Intro</b> - Add text intro\n\n"
        "<b>✂️ Editing:</b>\n"
        "• <b>Trim</b> - Cut video segments\n"
        "• <b>Metadata</b> - Edit file metadata\n"
        "• <b>Rename</b> - Custom output filename\n\n"
        "<b>🔹 Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/settings - Your settings\n"
        "/stats - Bot statistics\n"
        "/ping - Check bot latency\n"
    )
    
    await message.reply_text(help_text, reply_markup=close_button(user.id))


@bot.on_message(filters.command("ping") & filters.private)
async def ping_command(client: Client, message: Message):
    """Handle /ping command"""
    start = time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time()
    
    latency = (end - start) * 1000
    await msg.edit_text(f"🏓 <b>Pong!</b>\n\n<b>Latency:</b> {latency:.2f}ms")


@bot.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle /stats command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    db = get_db()
    
    # System stats
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # User count
    user_count = await db.get_user_count() if db else len(user_data)
    
    stats_text = (
        "<b>📊 Bot Statistics</b>\n\n"
        f"<b>👥 Total Users:</b> {user_count}\n\n"
        "<b>💻 System Info:</b>\n"
        f"• <b>CPU:</b> {cpu}%\n"
        f"• <b>RAM:</b> {ram.percent}% ({ram.used // (1024**3):.1f}GB / {ram.total // (1024**3):.1f}GB)\n"
        f"• <b>Disk:</b> {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)\n"
    )
    
    await message.reply_text(stats_text, reply_markup=close_button(message.from_user.id))


@bot.on_message(filters.command("settings") & filters.private)
async def settings_command(client: Client, message: Message):
    """Handle /settings command"""
    user = message.from_user
    
    if not is_authorized(user.id):
        return
    
    # Add user to DB if not exists (JIC)
    # Add user to DB if not exists (JIC)
    db = get_db()
    if db:
        await db.add_user(user.id, user.username, user.first_name)
    else:
        await message.reply_text("❌ <b>Database not connected.</b>\nCannot access settings.")
        return
    
    from bot.keyboards.settings_menu import open_settings
    menu = await open_settings(user.id)
    
    await message.reply_text("<b>⚙️ Settings Menu</b>", reply_markup=menu)


@bot.on_message(filters.command("vset") & filters.private)
async def vset_command(client: Client, message: Message):
    """Handle /vset command (View Settings) - Reference Bot Style"""
    user = message.from_user
    if not is_authorized(user.id):
        return

    db = get_db()
    if not db:
        await message.reply_text("❌ Database not connected.")
        return

    # Helper to format boolean
    def tick(val):
        return '☑️' if val else ''

    # Fetch all settings
    s = await db.get_user_settings(user.id)
    
    # Format Codecs
    video_codec = "H265 (HEVC)" if s.get('hevc') else "H264"
    audio_codec = (s.get('audio_codec') or "AAC").upper()
    if audio_codec == 'DD': audio_codec = 'AC3'
    
    # Values
    res = s.get('resolution') or "Source"
    if res == 'OG': res = "Source"
    
    tune = "Animation" if s.get('tune') else "Film"
    preset = (s.get('preset') or "medium").title()
    crf = s.get('crf', 26)
    ref = s.get('reframe') or "Pass"
    fps = s.get('frame') or "Source"
    
    # Audio
    asr = s.get('sample_rate') or "Source"
    abr = s.get('audio_bitrate') or "Source"
    chn = s.get('channels') or "Source"
    
    # Subs
    hardsub = tick(s.get('hardsub'))
    softsub = tick(s.get('subtitles'))
    
    # Watermark
    wm_enabled = tick(s.get('watermark_enabled'))
    meta_w = s.get('metadata_w') and "Weeb-Zone" or "Default"

    msg = f"""<b>Encode Settings:</b>

<b>📹 Video Settings</b>
Format : {s.get('output_format', 'MKV')}
Quality: {res}
Codec: {video_codec}
Aspect: {s.get('aspect') or 'Source'}
Reframe: {ref} | FPS: {fps}
Tune: {tune}
Preset: {preset}
Bits: {s.get('bits') or '8'} | CRF: {crf}
CABAC: {tick(s.get('cabac'))}

<b>📜 Subtitles Settings</b>
Hardsub {hardsub} | Softsub {softsub}

<b>©️ Watermark Settings</b>
Metadata: {meta_w}
Video {wm_enabled}

<b>🔊 Audio Settings</b>
Codec: {audio_codec}
Sample Rate : {asr}
Bit Rate: {abr}
Channels: {chn}
"""
    await message.reply_text(msg, reply_markup=close_button(user.id))


@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle /broadcast command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to broadcast it.")
        return
    
    db = get_db()
    if not db:
        await message.reply_text("Database not connected.")
        return
    
    users = await db.get_all_users()
    sent = 0
    failed = 0
    
    status_msg = await message.reply_text("📢 Broadcasting...")
    
    for user in users:
        try:
            await message.reply_to_message.copy(user['_id'])
            sent += 1
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"<b>📢 Broadcast Complete!</b>\n\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}"
    )


@bot.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    """Handle /restart command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    await message.reply_text("🔄 <b>Restarting bot...</b>")
    LOGGER.info("Restart command received")
    
    # Restart the bot
    os.execl(sys.executable, sys.executable, "-m", "bot")


@bot.on_message(filters.command("update") & filters.private)
async def update_command(client: Client, message: Message):
    """Handle /update command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    status_msg = await message.reply_text("🔄 <b>Pulling updates from GitHub...</b>")
    
    try:
        # Run git pull
        result = subprocess.run(
            ['git', 'pull'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout or result.stderr or "No output"
        
        if "Already up to date" in output:
            await status_msg.edit_text(
                "✅ <b>Already up to date!</b>\n\n"
                f"<code>{output[:500]}</code>"
            )
        elif result.returncode == 0:
            await status_msg.edit_text(
                "✅ <b>Update pulled successfully!</b>\n\n"
                f"<code>{output[:500]}</code>\n\n"
                "📦 <b>Installing requirements...</b>"
            )
            LOGGER.info(f"Update pulled: {output[:100]}")
            
            # PIP INSTALL
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    check=True
                )
            except Exception as e:
                LOGGER.error(f"Pip install failed: {e}")
                # Continue anyway? Or stop? Let's try to continue.
            
            await status_msg.edit_text("🔄 <b>Restarting bot...</b>")
            
            # Restart after update
            os.execl(sys.executable, sys.executable, "-m", "bot")
        else:
            await status_msg.edit_text(
                f"❌ <b>Update failed!</b>\n\n"
                f"<code>{output[:500]}</code>"
            )
            
    except subprocess.TimeoutExpired:
        await status_msg.edit_text("❌ <b>Update timed out!</b>")
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> {str(e)[:200]}")


@bot.on_message(filters.command("shell") & filters.private)
async def shell_command(client: Client, message: Message):
    """Handle /shell command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "<b>Usage:</b> <code>/shell command</code>\n\n"
            "<b>Example:</b> <code>/shell ls -la</code>"
        )
        return
    
    cmd = message.text.split(None, 1)[1]
    status_msg = await message.reply_text(f"⚙️ <b>Running:</b> <code>{cmd[:50]}</code>")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout or result.stderr or "No output"
        
        # Truncate if too long
        if len(output) > 4000:
            output = output[:4000] + "\n...(truncated)"
        
        await status_msg.edit_text(
            f"<b>Command:</b> <code>{cmd[:100]}</code>\n\n"
            f"<b>Output:</b>\n<code>{output}</code>"
        )
        
    except subprocess.TimeoutExpired:
        await status_msg.edit_text("❌ <b>Command timed out!</b>")
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> {str(e)[:200]}")


@bot.on_message(filters.command("log") & filters.private)
async def log_command(client: Client, message: Message):
    """Handle /log command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
    
    log_file = "logs/bot.log"
    
    if not os.path.exists(log_file):
        await message.reply_text("📝 No log file found.")
        return
    
    try:
        # Get last 50 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-50:] if len(lines) > 50 else lines
            log_content = ''.join(last_lines)
        
        if len(log_content) > 4000:
            log_content = log_content[-4000:]
        
        await message.reply_text(
            f"<b>📝 Last 50 log lines:</b>\n\n"
            f"<code>{log_content}</code>"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error reading log: {e}")


@bot.on_message(filters.command("unzip") & filters.private)
async def unzip_command(client: Client, message: Message):
    """Handle /unzip command"""
    user = message.from_user
    if not is_authorized(user.id):
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("❌ Reply to a document to unzip it.")
        return
        
    status_msg = await message.reply_text("⏳ Downloading file...")
    
    try:
        # Download
        from bot.handlers.file_handler import download_file
        file_path = await download_file(message.reply_to_message, status_msg)
        
        await status_msg.edit_text("⏳ Extracting...")
        
        output_dir = os.path.join(os.path.dirname(file_path), "extracted_" + str(time()))
        os.makedirs(output_dir, exist_ok=True)
        
        from bot.utils.archive import extract_archive
        success = await extract_archive(file_path, output_dir)
        
        if success:
            await status_msg.edit_text("✅ Extracted! Uploading contents...")
            
            # Upload extracted files
            files = []
            for root, _, filenames in os.walk(output_dir):
                for f in filenames:
                    files.append(os.path.join(root, f))
            
            if not files:
                await status_msg.edit_text("❌ Archive was empty.")
                return
                
            from bot.handlers.file_handler import upload_file
            # Upload each file (limit to reasonable amount?)
            count = 0
            for f in files:
                if count > 10:
                    await client.send_message(message.chat.id, "⚠️ Too many files, stopping upload.")
                    break
                await upload_file(client, message.chat.id, f, status_msg, caption=f"📄 {os.path.basename(f)}")
                count += 1
                
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Extraction failed.")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")


@bot.on_message(filters.command("zip") & filters.private)
async def zip_command(client: Client, message: Message):
    """Handle /zip command"""
    user = message.from_user
    if not is_authorized(user.id):
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a file/video to zip it.")
        return
        
    status_msg = await message.reply_text("⏳ Downloading file...")
    
    try:
        from bot.handlers.file_handler import download_file
        file_path = await download_file(message.reply_to_message, status_msg)
        
        await status_msg.edit_text("⏳ Archiving...")
        
        from bot.utils.archive import create_archive
        # Default name
        out_name = file_path + ".zip"
        archive_path = await create_archive(file_path, out_name, "zip")
        
        if archive_path:
            await status_msg.edit_text("✅ Archived! Uploading...")
            from bot.handlers.file_handler import upload_file
            await upload_file(client, message.chat.id, archive_path, status_msg, caption="📦 Archived File")
        else:
            await status_msg.edit_text("❌ Archiving failed.")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")


@bot.on_message(filters.command("thumb") & filters.private)
async def thumb_command(client: Client, message: Message):
    """Handle /thumb command (View/Set/Delete Thumbnail)"""
    user = message.from_user
    if not is_authorized(user.id):
        return

    db = get_db()
    thumbnail = await db.get_thumbnail(user.id) if db else None
    
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [
        [
            InlineKeyboardButton("Set/Replace Thumbnail", callback_data=f"set_thumb_{user.id}"),
            InlineKeyboardButton("Delete Thumbnail", callback_data=f"del_thumb_{user.id}")
        ],
        [
            InlineKeyboardButton("Close", callback_data=f"close_{user.id}")
        ]
    ]
    
    if thumbnail:
        await message.reply_photo(
            photo=thumbnail,
            caption="🖼️ <b>Your current custom thumbnail.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await message.reply_text(
            "🖼️ <b>You don't have a custom thumbnail set.</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


@bot.on_message(filters.command("reset") & filters.private)
async def reset_command(client: Client, message: Message):
    """Handle /reset command"""
    user = message.from_user
    if not is_authorized(user.id):
        return
        
    db = get_db()
    if db:
        await db.delete_user(user.id)
        await db.add_user(user.id, user.username, user.first_name)
    
    await message.reply_text("✅ <b>Settings have been reset to default!</b>")


@bot.on_message(filters.command("clean") & filters.private)
async def clean_command(client: Client, message: Message):
    """Handle /clean command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
        
    import shutil
    from bot import DOWNLOAD_DIR, OUTPUT_DIR
    
    status_msg = await message.reply_text("🧹 Cleaning cache...")
    
    try:
        # Clean downloads
        for item in os.listdir(DOWNLOAD_DIR):
            item_path = os.path.join(DOWNLOAD_DIR, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                
        # Clean outputs
        for item in os.listdir(OUTPUT_DIR):
            item_path = os.path.join(OUTPUT_DIR, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                
        await status_msg.edit_text("✅ <b>Cache cleaned successfully!</b>")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error during clean: {e}")


@bot.on_message(filters.command("dl") & filters.private)
async def dl_command(client: Client, message: Message):
    """Handle /dl command"""
    user = message.from_user
    if not is_authorized(user.id):
        return
        
    if not message.reply_to_message:
        await message.reply_text("Reply to a file/video to download and process it.")
        return
        
    # Trigger processing manually
    from bot.handlers.file_handler import handle_video, handle_audio
    msg = message.reply_to_message
    
    if msg.video or msg.document:
        await handle_video(client, msg)
    elif msg.audio:
        await handle_audio(client, msg)
    elif msg.text and (msg.text.startswith("http") or "http" in msg.text):
        # Extract URL logic
        url = msg.text
        if "http" in url and not url.startswith("http"):
             # Simple extraction if mixed with text, though user usually sends just link
             # For now assume mostly link
             # Grab first http match or just pass text
             pass
        
        from bot.handlers.file_handler import handle_url_logic
        await handle_url_logic(client, msg, url)
    else:
        await message.reply_text("❌ Unsupported media type. Reply to Video, Audio, or URL.")


@bot.on_message(filters.command("speedtest") & filters.private)
async def speedtest_command(client: Client, message: Message):
    """Handle /speedtest command - Owner only"""
    if message.from_user.id != OWNER_ID:
        return
        
    status_msg = await message.reply_text("🚀 Running speedtest...")
    
    try:
        import asyncio
        import json
        
        proc = await asyncio.create_subprocess_exec(
            'speedtest-cli', '--json',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            await status_msg.edit_text(f"❌ Speedtest failed: {stderr.decode().strip()}")
            return
            
        result = json.loads(stdout.decode())
        
        def humanbytes(size):
            # Simple helper
            power = 2**10
            n = 0
            power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
            while size > power:
                size /= power
                n += 1
            return f"{size:.2f} {power_labels[n]}B"
            
        caption = (
            f"<b>🚀 SPEEDTEST RESULT</b>\n\n"
            f"<b>Ping:</b> {result['ping']} ms\n"
            f"<b>Download:</b> {humanbytes(result['download'] / 8)}/s\n"
            f"<b>Upload:</b> {humanbytes(result['upload'] / 8)}/s\n"
            f"<b>ISP:</b> {result['client']['isp']}\n"
            f"<b>Country:</b> {result['server']['country']}"
        )
        
        try:
            await status_msg.delete()
        except:
            pass
            
        if result.get('share'):
            try:
                await message.reply_photo(photo=result['share'], caption=caption)
            except Exception as args:
                LOGGER.error(f"Failed to send speedtest image: {args}")
                await message.reply_text(caption + f"\n\n<b>Link:</b> <a href='{result['share']}'>View Image</a>")
        else:
            await message.reply_text(caption)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")


@bot.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    """Handle /status command"""
    user = message.from_user
    if not is_authorized(user.id):
        return
    
    # System Stats
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    
    # Active Tasks
    tasks = []
    for uid, data in user_data.items():
        if 'progress' in data and not data['progress'].cancelled:
             fname = data.get('file_name', 'Unknown')
             status = "Active"
             tasks.append(f"• User {uid}: {fname} ({status})")
             
    task_text = "\n".join(tasks) if tasks else "No active tasks."
    
    msg = (
        f"<b>📊 System Status</b>\n\n"
        f"<b>CPU:</b> {cpu}% | <b>RAM:</b> {ram.percent}%\n\n"
        f"<b>🔄 Active Tasks:</b>\n"
        f"{task_text}"
    )
    
    await message.reply_text(msg, reply_markup=close_button(user.id))


@bot.on_message(filters.command("queue") & filters.private)
async def queue_command(client: Client, message: Message):
    """Handle /queue command - Show active tasks"""
    user = message.from_user
    if not is_authorized(user.id):
        return
        
    tasks = []
    count = 0
    for uid, data in user_data.items():
        if 'progress' in data and not data['progress'].cancelled:
             fname = data.get('file_name', 'Unknown')
             op = data.get('operation', 'Unknown')
             tasks.append(f"<b>{count+1}.</b> {fname}\n   └ <i>{op}</i> (User: {uid})")
             count += 1
             
    if not tasks:
        await message.reply_text("🥱 <b>No Active Tasks.</b>")
    else:
        text = f"<b>🔄 Active Queue ({count})</b>\n\n" + "\n\n".join(tasks)
        await message.reply_text(text, reply_markup=close_button(user.id))


