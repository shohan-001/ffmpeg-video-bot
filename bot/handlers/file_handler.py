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
    """Handle received video files and subtitles"""
    user = message.from_user
    
    if not is_authorized(user.id):
        await message.reply_text("❌ You are not authorized.")
        return
    
    # helper to check subtitle
    def is_subtitle_file(filename: str) -> bool:
        if not filename: return False
        return any(filename.lower().endswith(ext) for ext in ['.srt', '.ass', '.ssa', '.vtt', '.sub'])

    fname = message.document.file_name if message.document else (message.video.file_name if message.video else "")
    
    # Get current state
    waiting_for = user_data.get(user.id, {}).get('waiting_for')
    
    # 1. Check if waiting for Subtitles
    if waiting_for in ['subtitle', 'hardsub']:
        if message.document and is_subtitle_file(fname):
            user_data[user.id]['subtitle_message'] = message
            user_data[user.id]['subtitle_name'] = fname
            
            # Determine operation
            operation = 'add_subtitle' if waiting_for == 'subtitle' else 'hardsub'
            user_data[user.id]['waiting_for'] = None
            
            await message.reply_text(
                "✅ Subtitle file received!\n\n"
                "Processing will begin shortly...",
                quote=True
            )
            
            from bot.handlers.message_handler import MockQuery
            from bot.handlers.callbacks import process_video
            await process_video(client, MockQuery(message, user), operation, {})
            return
        else:
            await message.reply_text("❌ Please send a valid subtitle file (.srt, .ass, .ssa, .vtt).")
            return

    # 2. Check if waiting for Second Video (Vid+Vid)
    if waiting_for == 'second_video':
        # Check if it's a video
        is_video = False
        if message.video: is_video = True
        if message.document and is_video_file(fname): is_video = True
        
        if not is_video:
            await message.reply_text("❌ Please send a valid video file.")
            return

        user_data[user.id]['second_video_message'] = message
        user_data[user.id]['second_video_name'] = fname
        user_data[user.id]['waiting_for'] = None
        
        from bot.handlers.message_handler import MockQuery
        from bot.handlers.callbacks import process_video
        
        await message.reply_text("✅ Second video received! Merging...", quote=True)
        await process_video(client, MockQuery(message, user), 'merge_video', {})
        return

    # 3. Check if it's a new Video
    is_video = False
    if message.video: is_video = True
    if message.document and is_video_file(fname): is_video = True
    
    if is_video:
        file_name = fname or f"video_{message.video.file_unique_id}.mp4"
        file_size = message.document.file_size if message.document else message.video.file_size
        
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
        return

    # 4. Check if random Subtitle (not waiting)
    if message.document and is_subtitle_file(fname):
        await message.reply_text(
            "ℹ️ To add subtitles, please send a video first, then select <b>Vid+Sub</b> from the menu.",
            quote=True
        )
        return

    # 5. Unknown/Invalid
    await message.reply_text(
        "❌ Please send a video file.\n\n"
        "Supported formats: mp4, mkv, avi, mov, webm, flv, etc."
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
        user_data[user.id]['waiting_for'] = None
        
        await message.reply_text(
            "✅ Audio file received!\n\n"
            "Processing will begin shortly...",
            quote=True
        )
        
        from bot.handlers.message_handler import MockQuery
        from bot.handlers.callbacks import process_video
        await process_video(client, MockQuery(message, user), 'add_audio', {})
        
    else:
        await message.reply_text(
            "ℹ️ Send a video first, then select <b>Vid+Aud</b> to add this audio.",
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
        user_data[user.id]['waiting_for'] = None
        
        await message.reply_text(
            "✅ Watermark image received!\n\n"
            "Now configure position, opacity, etc.",
            quote=True
        )
        # Note: We don't verify 'watermark' operation here because we still need to apply settings.
        # We just go back to watermark menu (or show it).
        # But we need to update settings to say we have an image.
        if 'watermark_settings' not in user_data[user.id]:
            user_data[user.id]['watermark_settings'] = {}
        # We don't save path yet, we download on apply.
        
        from bot.keyboards.menus import watermark_menu
        await message.reply_text(
            "Image saved. Configure settings:",
            reply_markup=watermark_menu(user.id)
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
    progress = Progress(status_msg, "📥 Downloading", user_id=uid, filename=file_name)
    
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


async def upload_file(client: Client, chat_id: int, file_path: str | list, status_msg: Message, caption: str = None, user_id: int = None):
    """Upload file with progress"""
    
    # Handle list of files (Media Group)
    if isinstance(file_path, list):
        from pyrogram.types import InputMediaPhoto
        media = []
        for f in file_path:
            # Assume photos for now (screenshots)
            media.append(InputMediaPhoto(f))
        
        await status_msg.edit_text("📤 Uploading album...")
        try:
            await client.send_media_group(chat_id, media)
        except Exception as e:
            await status_msg.edit_text(f"❌ Upload failed: {e}")
            raise e
        return

        return
    
    file_name = os.path.basename(file_path) if isinstance(file_path, str) else "Album"
    progress = Progress(status_msg, "📤 Uploading", user_id=user_id, filename=file_name)
    
    # Store progress for cancellation
    if user_id and user_id in user_data:
        user_data[user_id]['progress'] = progress
    
    file_size = 0  # Will be set below or calculated
    if isinstance(file_path, str):
         file_size = os.path.getsize(file_path)
         # file_name already set
    
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
