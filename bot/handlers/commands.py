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


# ─────────────────────────────────────────────────────────────
# Group Authorization Command
# ─────────────────────────────────────────────────────────────
@bot.on_message(filters.command("authgrp"))
async def authgrp_command(client: Client, message: Message):
    """Handle /authgrp command - Authorize groups for bot usage"""
    from pyrogram.enums import ChatType
    
    # Only owner can authorize groups
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ This command is owner-only.")
        return
    
    db = get_db()
    if not db:
        await message.reply_text("❌ Database not connected.")
        return
    
    chat = message.chat
    args = message.text.split()
    
    # If run in a group by admin, auto-authorize that group
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        group_id = chat.id
        
        # Check if already authorized
        if await db.is_group_authorized(group_id):
            # Toggle: remove if already authorized
            await db.remove_authorized_group(group_id)
            await message.reply_text(
                f"✅ <b>Group De-authorized!</b>\n\n"
                f"<b>Group:</b> {chat.title}\n"
                f"<b>ID:</b> <code>{group_id}</code>\n\n"
                f"Bot will no longer work in this group."
            )
        else:
            # Authorize
            await db.add_authorized_group(group_id)
            await message.reply_text(
                f"✅ <b>Group Authorized!</b>\n\n"
                f"<b>Group:</b> {chat.title}\n"
                f"<b>ID:</b> <code>{group_id}</code>\n\n"
                f"Bot is now active in this group!"
            )
        return
    
    # If run in private, show usage or handle args
    if len(args) == 1:
        # Show list of authorized groups
        groups = await db.get_authorized_groups()
        if groups:
            group_list = "\n".join([f"• <code>{g}</code>" for g in groups])
            await message.reply_text(
                f"<b>📋 Authorized Groups</b>\n\n"
                f"{group_list}\n\n"
                f"<b>Usage:</b>\n"
                f"• Run <code>/authgrp</code> IN a group to toggle\n"
                f"• <code>/authgrp add GroupID</code>\n"
                f"• <code>/authgrp remove GroupID</code>"
            )
        else:
            await message.reply_text(
                f"<b>📋 No Authorized Groups</b>\n\n"
                f"<b>Usage:</b>\n"
                f"• Run <code>/authgrp</code> IN a group to authorize\n"
                f"• <code>/authgrp add GroupID</code>"
            )
        return
    
    action = args[1].lower()
    
    if action in ["add", "remove"] and len(args) >= 3:
        try:
            group_id = int(args[2])
        except ValueError:
            await message.reply_text("❌ Invalid group ID. Must be a number.")
            return
        
        if action == "add":
            if await db.add_authorized_group(group_id):
                await message.reply_text(f"✅ Group <code>{group_id}</code> authorized!")
            else:
                await message.reply_text(f"ℹ️ Group <code>{group_id}</code> already authorized.")
        else:
            if await db.remove_authorized_group(group_id):
                await message.reply_text(f"✅ Group <code>{group_id}</code> removed!")
            else:
                await message.reply_text(f"ℹ️ Group <code>{group_id}</code> not in list.")
    else:
        await message.reply_text(
            "❌ <b>Invalid usage</b>\n\n"
            "<b>Usage:</b>\n"
            "• Run <code>/authgrp</code> IN a group to toggle\n"
            "• <code>/authgrp add GroupID</code>\n"
            "• <code>/authgrp remove GroupID</code>"
        )


# ─────────────────────────────────────────────────────────────
# Cookie Management Commands
# ─────────────────────────────────────────────────────────────
@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_command(client: Client, message: Message):
    """Handle /cookies command - Manage yt-dlp cookies"""
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ This command is owner-only.")
        return
    
    db = get_db()
    if not db:
        await message.reply_text("❌ Database not connected.")
        return
    
    args = message.text.split()
    
    if len(args) == 1:
        # Show status
        has_global = await db.has_cookies(0)
        status = "✅ Cookies are set" if has_global else "❌ No cookies set"
        
        await message.reply_text(
            f"<b>🍪 YT-DLP Cookies Status</b>\n\n"
            f"{status}\n\n"
            f"<b>Commands:</b>\n"
            f"• <code>/cookies set</code> - Upload cookies.txt file\n"
            f"• <code>/cookies clear</code> - Delete stored cookies\n\n"
            f"<b>How to get cookies:</b>\n"
            f"1. Install 'Get cookies.txt' browser extension\n"
            f"2. Log in to YouTube\n"
            f"3. Export cookies as cookies.txt\n"
            f"4. Upload here with <code>/cookies set</code>"
        )
        return
    
    action = args[1].lower()
    
    if action == "set":
        user_data[message.from_user.id] = user_data.get(message.from_user.id, {})
        user_data[message.from_user.id]['waiting_for'] = 'cookies_file'
        await message.reply_text(
            "📤 <b>Upload your cookies.txt file now.</b>\n\n"
            "The file should be in Netscape cookie format.\n"
            "Send /cancel to abort."
        )
    
    elif action == "clear":
        await db.delete_cookies(0)
        await message.reply_text("✅ <b>Cookies deleted successfully.</b>")
    
    elif action == "test":
        # Test if cookies are accessible
        cookies_data = await db.get_cookies(0)
        if cookies_data:
            lines = cookies_data.split('\n')
            youtube_lines = [l for l in lines if 'youtube' in l.lower() or 'google' in l.lower()]
            await message.reply_text(
                f"✅ <b>Cookies found in database!</b>\n\n"
                f"<b>Total lines:</b> {len(lines)}\n"
                f"<b>YouTube/Google entries:</b> {len(youtube_lines)}\n\n"
                f"<b>First few YouTube entries:</b>\n"
                f"<code>{chr(10).join(youtube_lines[:5])[:500]}</code>"
            )
        else:
            await message.reply_text("❌ No cookies found in database.")
    
    else:
        await message.reply_text("❌ Unknown action. Use <code>/cookies set</code>, <code>/cookies test</code>, or <code>/cookies clear</code>")


@bot.on_message(filters.document & filters.private, group=2)
async def handle_document_upload(client: Client, message: Message):
    """Handle document uploads for cookies and credentials only"""
    user = message.from_user
    
    if user.id not in user_data:
        return
    
    waiting_for = user_data[user.id].get('waiting_for')
    
    # Only handle cookies and gdrive credentials, let other handlers process other docs
    if waiting_for not in ['cookies_file', 'gdrive_credentials']:
        return
    
    if waiting_for == 'cookies_file':
        # Handle cookies.txt upload
        user_data[user.id]['waiting_for'] = None
        
        doc = message.document
        if doc.file_size > 1024 * 1024:  # 1MB limit
            await message.reply_text("❌ File too large. Cookies file should be under 1MB.")
            return
        
        status_msg = await message.reply_text("⏳ Processing cookies file...")
        
        try:
            # Download file
            file_path = await message.download()
            
            # Read content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                cookies_data = f.read()
            
            # Validate it looks like a cookies file
            if not ('# Netscape HTTP Cookie' in cookies_data or '.youtube.com' in cookies_data or 'TRUE' in cookies_data):
                await status_msg.edit_text("❌ This doesn't look like a valid cookies.txt file.")
                os.remove(file_path)
                return
            
            # Store in database
            db = get_db()
            await db.set_cookies(cookies_data, 0)  # Global cookies
            
            # Cleanup
            os.remove(file_path)
            
            await status_msg.edit_text(
                "✅ <b>Cookies saved successfully!</b>\n\n"
                "YouTube downloads should now work better."
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")
    
    elif waiting_for == 'gdrive_credentials':
        # Handle credentials.json upload
        user_data[user.id]['waiting_for'] = None
        
        doc = message.document
        if not doc.file_name.endswith('.json'):
            await message.reply_text("❌ Please upload a .json file.")
            return
        
        if doc.file_size > 100 * 1024:  # 100KB limit
            await message.reply_text("❌ File too large for credentials.")
            return
        
        status_msg = await message.reply_text("⏳ Processing credentials...")
        
        try:
            file_path = await message.download()
            
            with open(file_path, 'r') as f:
                creds_data = f.read()
            
            # Basic validation
            import json
            creds_json = json.loads(creds_data)
            
            # Check identifying fields
            is_service_account = creds_json.get('type') == 'service_account'
            has_required_fields = 'client_email' in creds_json and 'private_key' in creds_json
            
            # OAuth Identification
            is_oauth = 'web' in creds_json or 'installed' in creds_json
            
            db = get_db()

            if is_oauth:
                await db.set_gdrive_client_secrets(creds_data)
                await status_msg.edit_text(
                    "✅ <b>OAuth Client Secrets Uploaded!</b>\n\n"
                    "Now authorize the bot:\n"
                    "1. Run <code>/gdrive login</code>\n"
                    "2. Click the link and get the code\n"
                    "3. Run <code>/gdrive auth &lt;code&gt;</code>"
                )
                os.remove(file_path)
                return

            if not (is_service_account or has_required_fields):
                await status_msg.edit_text(
                    "❌ <b>Invalid JSON</b>\n\n"
                    "This looks like neither a Service Account key nor an OAuth Client Secret."
                )
                os.remove(file_path)
                return
            
            # Store in database
            db = get_db()
            await db.set_gdrive_credentials(creds_data)
            
            # Re-initialize GDrive immediately
            from bot.utils.gdrive import get_gdrive
            await get_gdrive().initialize()
            
            os.remove(file_path)
            
            await status_msg.edit_text(
                "✅ <b>Google Drive credentials saved!</b>\n\n"
                "Make sure to share your GDrive folder with:\n"
                f"<code>{creds_json.get('client_email', 'the service account email')}</code>"
            )
        except json.JSONDecodeError:
            await status_msg.edit_text("❌ Invalid JSON file.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Google Drive Credentials Command
# ─────────────────────────────────────────────────────────────
@bot.on_message(filters.command("gdrive") & filters.private)
async def gdrive_command(client: Client, message: Message):
    """Handle /gdrive command - Manage Google Drive credentials"""
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ This command is owner-only.")
        return
    
    db = get_db()
    if not db:
        await message.reply_text("❌ Database not connected.")
        return
    
    args = message.text.split()
    
    if len(args) == 1:
        # Show status
        has_creds = await db.has_gdrive_credentials()
        from bot import GDRIVE_ENABLED, GDRIVE_FOLDER_ID as ENV_FOLDER_ID
        
        # Prefer DB folder ID
        db_folder_id = await db.get_gdrive_folder_id()
        folder_id = db_folder_id or ENV_FOLDER_ID
        
        status = "✅ Credentials set" if has_creds else "❌ No credentials"
        enabled = "✅ Enabled" if GDRIVE_ENABLED else "❌ Disabled"
        folder = f"<code>{folder_id}</code>" if folder_id else "❌ Not set"
        
        await message.reply_text(
            f"<b>☁️ Google Drive Status</b>\n\n"
            f"<b>GDrive Upload:</b> {enabled}\n"
            f"<b>Credentials:</b> {status}\n"
            f"<b>Folder ID:</b> {folder}\n\n"
            f"<b>Commands:</b>\n"
            f"• <code>/gdrive set</code> - Upload credentials.json\n"
            f"• <code>/gdrive folder &lt;ID&gt;</code> - Set Folder ID\n"
            f"• <code>/gdrive clear</code> - Delete credentials\n\n"
            f"<b>Setup:</b>\n"
            f"1. Create a Google Cloud project\n"
            f"2. Enable Google Drive API\n"
            f"3. Create a Service Account\n"
            f"4. Download credentials.json\n"
            f"5. Upload with <code>/gdrive set</code>"
        )
        return
    
    action = args[1].lower()

    if action == "folder":
        if len(args) < 3:
            await message.reply_text("❌ Usage: <code>/gdrive folder <FOLDER_ID></code>")
            return
        
        folder_id = args[2].strip()
        await db.set_gdrive_folder_id(folder_id)
        await message.reply_text(f"✅ <b>Google Drive Folder ID set!</b>\n\nID: <code>{folder_id}</code>")
        return

    elif action == "login":
        secrets_json = await db.get_gdrive_client_secrets()
        if not secrets_json:
            await message.reply_text(
                "❌ <b>No OAuth Credentials found!</b>\n\n"
                "Please upload your <code>client_secrets.json</code> (Desktop App) using <code>/gdrive set</code>."
            )
            return
            
        try:
            from bot.utils.gdrive import get_gdrive
            import json
            secrets = json.loads(secrets_json)
            auth_url = await get_gdrive().generate_oauth_url(secrets)
            await message.reply_text(
                f"<b>🔐 Google Drive Login</b>\n\n"
                f"1. <a href='{auth_url}'>Click here to Authorize</a>\n"
                f"2. Copy the authorization code\n"
                f"3. Send: <code>/gdrive auth &lt;code&gt;</code>"
            )
        except Exception as e:
            await message.reply_text(f"❌ Error generating login URL: {e}")
        return

    elif action == "auth":
        if len(args) < 3:
            await message.reply_text("❌ Usage: <code>/gdrive auth &lt;code&gt;</code>")
            return
            
        code = args[2].strip()
        secrets_json = await db.get_gdrive_client_secrets()
        if not secrets_json:
             await message.reply_text("❌ OAuth Credentials missing.")
             return

        try:
            from bot.utils.gdrive import get_gdrive
            import json
            secrets = json.loads(secrets_json)
            token_json = await get_gdrive().exchange_oauth_code(secrets, code)
            
            await db.set_gdrive_oauth_token(token_json)
            await get_gdrive().initialize()
            
            await message.reply_text("✅ <b>Login Successful!</b>\n\nThe bot is now authorized to upload to your account.")
        except Exception as e:
            await message.reply_text(f"❌ Authorization failed: {e}")
        return
    
    if action == "set":
        user_data[message.from_user.id] = user_data.get(message.from_user.id, {})
        user_data[message.from_user.id]['waiting_for'] = 'gdrive_credentials'
        await message.reply_text(
            "📤 <b>Upload your credentials.json file now.</b>\n\n"
            "This should be a Google Service Account JSON file.\n"
            "Send /cancel to abort."
        )
    
    elif action == "clear":
        await db.delete_gdrive_credentials()
        await message.reply_text("✅ <b>Google Drive credentials deleted.</b>")
    
    else:
        await message.reply_text("❌ Unknown action. Use <code>/gdrive set</code> or <code>/gdrive clear</code>")
