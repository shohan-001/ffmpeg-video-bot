#!/usr/bin/env python3
"""File handler for receiving videos"""

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from bot import bot, OWNER_ID, AUTHORIZED_USERS, DOWNLOAD_DIR, LOGGER, user_data
from bot.keyboards.menus import main_menu, close_button
from bot.ffmpeg.core import get_video_info, format_media_info
from bot.utils.helpers import is_video_file, get_readable_file_size
from bot.utils.progress import Progress


# Helper function to check authorization
def is_authorized(user_id: int) -> bool:
    if not AUTHORIZED_USERS:
        return True
    return user_id in AUTHORIZED_USERS or user_id == OWNER_ID


@bot.on_message(filters.private & (filters.video | filters.document))
async def handle_video(client: Client, message: Message):
    """Handle received video files"""
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ You are not authorized.")
        return
    
    # Check if it's a video
    if message.document:
        file_name = message.document.file_name
        file_size = message.document.file_size
        if not is_video_file(file_name):
            await message.reply_text(
                "❌ Please send a video file.\n\n"
                "Supported formats: mp4, mkv, avi, mov, webm, flv, etc."
            )
            return
    else:
        file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
        file_size = message.video.file_size
    
    # Store file info for this user
    user_data[user.id] = {
        'message_id': message.id,
        'file_name': file_name,
        'file_size': file_size,
        'file_path': None,
        'operation': None,
        'settings': user_data.get(user.id, {}).get('settings', {}),
    }
    
    info_text = (
        f"<b>📁 File Received!</b>\n\n"
        f"<b>📄 Name:</b> <code>{file_name}</code>\n"
        f"<b>💾 Size:</b> {get_readable_file_size(file_size)}\n\n"
        f"<b>Select an operation from the menu below:</b>"
    )
    
    await message.reply_text(
        info_text,
        reply_markup=main_menu(user.id),
        quote=True
    )


@bot.on_message(filters.private & filters.audio)
async def handle_audio(client: Client, message: Message):
    """Handle audio files (for Vid+Aud operation)"""
    user = message.from_user
    
    if not is_authorized(user.id):
        return
    
    # Check if user has a pending video operation
    if user.id in user_data and user_data[user.id].get('waiting_for') == 'audio':
        user_data[user.id]['audio_message'] = message
        user_data[user.id]['audio_name'] = message.audio.file_name if message.audio else "audio.mp3"
        
        await message.reply_text(
            "✅ Audio file received!\n\n"
            "Processing will begin shortly...",
            quote=True
        )
        # Trigger processing (callback handler will handle this)
    else:
        await message.reply_text(
            "ℹ️ Send a video first, then select <b>Vid+Aud</b> to add this audio.",
            quote=True
        )


@bot.on_message(filters.private & (filters.document))
async def handle_subtitle(client: Client, message: Message):
    """Handle subtitle files (for Vid+Sub and Hardsub)"""
    user = message.from_user
    
    if not is_authorized(user.id):
        return
    
    if not message.document:
        return
    
    file_name = message.document.file_name.lower()
    subtitle_exts = ['.srt', '.ass', '.ssa', '.vtt', '.sub']
    
    if any(file_name.endswith(ext) for ext in subtitle_exts):
        if user.id in user_data and user_data[user.id].get('waiting_for') in ['subtitle', 'hardsub']:
            user_data[user.id]['subtitle_message'] = message
            user_data[user.id]['subtitle_name'] = message.document.file_name
            
            await message.reply_text(
                "✅ Subtitle file received!\n\n"
                "Processing will begin shortly...",
                quote=True
            )


@bot.on_message(filters.private & filters.photo)
async def handle_photo(client: Client, message: Message):
    """Handle photos (for watermark)"""
    user = message.from_user
    
    if not is_authorized(user.id):
        return
    
    if user.id in user_data and user_data[user.id].get('waiting_for') == 'watermark_image':
        user_data[user.id]['watermark_message'] = message
        
        await message.reply_text(
            "✅ Watermark image received!\n\n"
            "Processing will begin shortly...",
            quote=True
        )


async def download_file(message: Message, status_msg: Message, user_id: int = None) -> str:
    """Download file from message with progress"""
    user = message.from_user
    uid = user_id or user.id
    
    # Create user directory
    user_dir = os.path.join(DOWNLOAD_DIR, str(uid))
    os.makedirs(user_dir, exist_ok=True)
    
    # Get file name
    if message.video:
        file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
    elif message.document:
        file_name = message.document.file_name
    elif message.audio:
        file_name = message.audio.file_name or f"audio_{message.audio.file_unique_id}.mp3"
    else:
        file_name = "unknown_file"
    
    file_path = os.path.join(user_dir, file_name)
    
    # Create progress with cancel button
    progress = Progress(status_msg, "📥 Downloading", user_id=uid)
    
    # Store progress instance for cancellation
    if uid in user_data:
        user_data[uid]['progress'] = progress
    
    try:
        await message.download(
            file_name=file_path,
            progress=progress.progress_callback
        )
    except Exception as e:
        if progress.cancelled:
            raise asyncio.CancelledError("Cancelled by user")
        raise e
    
    return file_path


async def upload_file(client: Client, chat_id: int, file_path: str, status_msg: Message, caption: str = None, user_id: int = None):
    """Upload file with progress"""
    progress = Progress(status_msg, "📤 Uploading", user_id=user_id)
    
    # Store progress for cancellation
    if user_id and user_id in user_data:
        user_data[user_id]['progress'] = progress
    
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    
    # Decide upload method based on file type
    video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
    ext = os.path.splitext(file_name)[1].lower()
    
    try:
        if ext in video_exts:
            await client.send_video(
                chat_id,
                file_path,
                caption=caption or f"✅ <code>{file_name}</code>",
                progress=progress.progress_callback
            )
        else:
            await client.send_document(
                chat_id,
                file_path,
                caption=caption or f"✅ <code>{file_name}</code>",
                progress=progress.progress_callback
            )
    except Exception as e:
        if progress.cancelled:
            raise asyncio.CancelledError("Cancelled by user")
        raise e
