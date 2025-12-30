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
    
    db = get_db()
    if db:
        settings = await db.get_user_settings(user.id)
    else:
        settings = {}
    
    settings_text = (
        f"<b>⚙️ Your Settings</b>\n\n"
        f"<b>Video Codec:</b> {settings.get('video_codec', 'libx264')}\n"
        f"<b>Audio Codec:</b> {settings.get('audio_codec', 'aac')}\n"
        f"<b>CRF Quality:</b> {settings.get('crf', 23)}\n"
        f"<b>Preset:</b> {settings.get('preset', 'medium')}\n"
        f"<b>Resolution:</b> {settings.get('resolution', 'Original')}\n"
        f"<b>Keep Source:</b> {'✅' if settings.get('keep_source') else '❌'}\n"
        f"<b>Watermark:</b> {'✅' if settings.get('watermark_enabled') else '❌'}\n"
    )
    
    await message.reply_text(settings_text, reply_markup=close_button(user.id))


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
                "🔄 <b>Restarting bot...</b>"
            )
            LOGGER.info(f"Update pulled: {output[:100]}")
            
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

