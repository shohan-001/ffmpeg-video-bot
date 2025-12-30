#!/usr/bin/env python3
"""Callback query handlers for inline buttons"""

import os
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from bot import bot, OWNER_ID, DOWNLOAD_DIR, OUTPUT_DIR, LOGGER, user_data, GDRIVE_ENABLED, GDRIVE_FOLDER_ID
from bot.keyboards.menus import (
    main_menu, encode_menu, preset_menu, resolution_menu,
    convert_menu, extract_menu, remove_menu, watermark_menu,
    watermark_position_menu, audio_format_menu, confirm_menu,
    close_button, speed_menu, rotate_menu, after_process_menu
)
from bot.handlers.file_handler import download_file, upload_file
from bot.ffmpeg import *
from bot.utils.progress import FFmpegProgress
from bot.utils.helpers import sanitize_filename, get_readable_file_size
from bot.utils.gdrive import get_gdrive, init_gdrive


@bot.on_callback_query(filters.regex(r"^close_"))
async def close_callback(client: Client, query: CallbackQuery):
    """Handle close button"""
    await query.message.delete()
    await query.answer("Closed!")


@bot.on_callback_query(filters.regex(r"^cancel_process_"))
async def cancel_process_callback(client: Client, query: CallbackQuery):
    """Cancel ongoing download/upload/processing"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    # Cancel progress
    if user_id in user_data and 'progress' in user_data[user_id]:
        user_data[user_id]['progress'].cancel()
        
    await query.answer("⏹️ Cancelling...", show_alert=True)
    
    try:
        await query.message.edit_text("❌ <b>Cancelled by user</b>")
    except:
        pass
    
    # Cleanup any partial files
    if user_id in user_data:
        if 'file_path' in user_data[user_id] and user_data[user_id]['file_path']:
            try:
                os.remove(user_data[user_id]['file_path'])
            except:
                pass
        if 'output_path' in user_data[user_id]:
            try:
                os.remove(user_data[user_id]['output_path'])
            except:
                pass


@bot.on_callback_query(filters.regex(r"^main_"))
async def main_menu_callback(client: Client, query: CallbackQuery):
    """Return to main menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_reply_markup(main_menu(user_id))
    await query.answer()


@bot.on_callback_query(filters.regex(r"^metadata_"))
async def metadata_callback(client: Client, query: CallbackQuery):
    """Handle MegaMetaData"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'metadata'
    user_data[user_id]['waiting_for'] = 'metadata_input'
    
    await query.message.edit_text(
        "<b>📝 MegaMetaData</b>\n\n"
        "Send me the metadata in this format:\n\n"
        "<code>title: Your Title\n"
        "author: Author Name\n"
        "album: Album Name\n"
        "year: 2026</code>\n\n"
        "Or send just the title.",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^encode_"))
async def encode_callback(client: Client, query: CallbackQuery):
    """Handle Encode menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'encode'
    
    # Show current encode settings
    settings = user_data[user_id].get('settings', {})
    
    await query.message.edit_text(
        "<b>⚙️ Encode Settings</b>\n\n"
        f"<b>Preset:</b> {settings.get('preset', 'medium')}\n"
        f"<b>CRF:</b> {settings.get('crf', 23)}\n"
        f"<b>Video Codec:</b> {settings.get('video_codec', 'libx264')}\n"
        f"<b>Audio Codec:</b> {settings.get('audio_codec', 'aac')}\n"
        f"<b>Resolution:</b> {settings.get('resolution', 'Original')}\n\n"
        "Select an option to change:",
        reply_markup=encode_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_preset_"))
async def preset_callback(client: Client, query: CallbackQuery):
    """Show preset selection menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>📊 Select Encoding Preset</b>\n\n"
        "Faster = Lower quality\n"
        "Slower = Higher quality",
        reply_markup=preset_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^preset_"))
async def set_preset_callback(client: Client, query: CallbackQuery):
    """Set encoding preset"""
    parts = query.data.split("_")
    preset = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if 'settings' not in user_data[user_id]:
        user_data[user_id]['settings'] = {}
    
    user_data[user_id]['settings']['preset'] = preset
    await query.answer(f"Preset set to: {preset}")
    
    # Return to encode menu
    await encode_callback(client, query)


@bot.on_callback_query(filters.regex(r"^enc_res_"))
async def resolution_callback(client: Client, query: CallbackQuery):
    """Show resolution selection menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>📐 Select Resolution</b>",
        reply_markup=resolution_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^convert_"))
async def convert_callback(client: Client, query: CallbackQuery):
    """Handle Convert menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'convert'
    
    await query.message.edit_text(
        "<b>🔄 Convert Format</b>\n\n"
        "Select output format:",
        reply_markup=convert_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^format_"))
async def format_selected_callback(client: Client, query: CallbackQuery):
    """Handle format selection and start conversion"""
    parts = query.data.split("_")
    fmt = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer(f"Converting to {fmt}...")
    
    # Start processing
    await process_video(client, query, 'convert', {'format': fmt})


@bot.on_callback_query(filters.regex(r"^extract_"))
async def extract_callback(client: Client, query: CallbackQuery):
    """Handle Extract menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>📤 Extract Streams</b>\n\n"
        "Choose what to extract:",
        reply_markup=extract_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^ext_audio_"))
async def extract_audio_callback(client: Client, query: CallbackQuery):
    """Show audio format selection"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>🔊 Extract Audio</b>\n\n"
        "Select output format:",
        reply_markup=audio_format_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^audiofmt_"))
async def audio_format_callback(client: Client, query: CallbackQuery):
    """Extract audio in selected format"""
    parts = query.data.split("_")
    fmt = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer(f"Extracting audio as {fmt}...")
    await process_video(client, query, 'extract_audio', {'format': fmt})


@bot.on_callback_query(filters.regex(r"^ext_video_"))
async def extract_video_callback(client: Client, query: CallbackQuery):
    """Extract video stream only"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Extracting video stream...")
    await process_video(client, query, 'extract_video', {})


@bot.on_callback_query(filters.regex(r"^ext_subs_"))
async def extract_subs_callback(client: Client, query: CallbackQuery):
    """Extract subtitles"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Extracting subtitles...")
    await process_video(client, query, 'extract_subs', {})


@bot.on_callback_query(filters.regex(r"^ext_thumb_"))
async def extract_thumb_callback(client: Client, query: CallbackQuery):
    """Extract thumbnail"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Extracting thumbnail...")
    await process_video(client, query, 'extract_thumb', {})


@bot.on_callback_query(filters.regex(r"^ext_ss_"))
async def extract_screenshots_callback(client: Client, query: CallbackQuery):
    """Extract screenshots"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Extracting screenshots...")
    await process_video(client, query, 'extract_screenshots', {})


@bot.on_callback_query(filters.regex(r"^remove_"))
async def remove_callback(client: Client, query: CallbackQuery):
    """Handle Remove menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>❌ Remove Streams</b>\n\n"
        "Choose what to remove:",
        reply_markup=remove_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^rem_audio_"))
async def remove_audio_callback(client: Client, query: CallbackQuery):
    """Remove audio from video"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Removing audio...")
    await process_video(client, query, 'remove_audio', {})


@bot.on_callback_query(filters.regex(r"^watermark_"))
async def watermark_callback(client: Client, query: CallbackQuery):
    """Handle Watermark menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>💧 Watermark</b>\n\n"
        "Choose watermark type:",
        reply_markup=watermark_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^wm_text_"))
async def watermark_text_callback(client: Client, query: CallbackQuery):
    """Request watermark text"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'watermark_text'
    user_data[user_id]['waiting_for'] = 'watermark_text'
    
    await query.message.edit_text(
        "<b>📝 Text Watermark</b>\n\n"
        "Send me the watermark text:",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^wm_image_"))
async def watermark_image_callback(client: Client, query: CallbackQuery):
    """Request watermark image"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'watermark_image'
    user_data[user_id]['waiting_for'] = 'watermark_image'
    
    await query.message.edit_text(
        "<b>🖼️ Image Watermark</b>\n\n"
        "Send me the watermark image:",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^trim_"))
async def trim_callback(client: Client, query: CallbackQuery):
    """Handle Trim menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'trim'
    user_data[user_id]['waiting_for'] = 'trim_input'
    
    await query.message.edit_text(
        "<b>✂️ Trim Video</b>\n\n"
        "Send me the trim times in format:\n\n"
        "<code>start_time end_time</code>\n\n"
        "Examples:\n"
        "• <code>00:00:30 00:02:00</code> (from 30s to 2min)\n"
        "• <code>10 120</code> (from 10s to 120s)\n"
        "• <code>00:01:00</code> (from 1min to end)",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^hardsub_"))
async def hardsub_callback(client: Client, query: CallbackQuery):
    """Handle Hardsub"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'hardsub'
    user_data[user_id]['waiting_for'] = 'hardsub'
    
    await query.message.edit_text(
        "<b>🔥 Hardsub (Burn Subtitles)</b>\n\n"
        "Send me the subtitle file (.srt, .ass, .ssa, .vtt)\n\n"
        "Subtitles will be permanently burned into the video.",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^vidsub_"))
async def vidsub_callback(client: Client, query: CallbackQuery):
    """Handle Vid+Sub"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'add_subtitle'
    user_data[user_id]['waiting_for'] = 'subtitle'
    
    await query.message.edit_text(
        "<b>📺 Vid+Sub</b>\n\n"
        "Send me the subtitle file (.srt, .ass, .ssa, .vtt)\n\n"
        "Subtitles will be added as a soft track (can be toggled).",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^vidaud_"))
async def vidaud_callback(client: Client, query: CallbackQuery):
    """Handle Vid+Aud"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['operation'] = 'add_audio'
    user_data[user_id]['waiting_for'] = 'audio'
    
    await query.message.edit_text(
        "<b>🔊 Vid+Aud</b>\n\n"
        "Send me the audio file to add.",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client: Client, query: CallbackQuery):
    """Handle Rename"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['waiting_for'] = 'rename'
    
    await query.message.edit_text(
        "<b>✏️ Rename</b>\n\n"
        "Send me the new filename (without extension):",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^keepsrc_"))
async def keepsource_callback(client: Client, query: CallbackQuery):
    """Toggle keep source"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if 'settings' not in user_data[user_id]:
        user_data[user_id]['settings'] = {}
    
    current = user_data[user_id]['settings'].get('keep_source', False)
    user_data[user_id]['settings']['keep_source'] = not current
    
    status = "enabled" if not current else "disabled"
    await query.answer(f"Keep Source {status}!")


# Main processing function
async def process_video(client: Client, query: CallbackQuery, operation: str, options: dict):
    """Process video with specified operation"""
    user_id = query.from_user.id
    
    if user_id not in user_data:
        await query.message.edit_text("❌ No video found. Send a video first.")
        return
    
    # Get original message with the video
    original_msg = user_data[user_id].get('message_id')
    if not original_msg:
        await query.message.edit_text("❌ No video found. Send a video first.")
        return
    
    status_msg = await query.message.edit_text("⏳ Starting process...")
    
    try:
        # Get the original message
        video_msg = await client.get_messages(query.message.chat.id, original_msg)
        
        # Download video
        await status_msg.edit_text("📥 Downloading video...")
        input_path = await download_file(video_msg, status_msg)
        user_data[user_id]['file_path'] = input_path
        
        # Generate output path
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        ext = os.path.splitext(input_path)[1]
        output_dir = os.path.join(OUTPUT_DIR, str(user_id))
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{base_name}_processed{ext}")
        
        # Get duration for progress
        duration = await FFmpeg(input_path).get_duration()
        progress = FFmpegProgress(status_msg, duration, f"Processing ({operation})")
        
        await status_msg.edit_text(f"⚙️ Processing: {operation}...")
        
        # Execute operation
        success = False
        error = ""
        
        if operation == 'convert':
            fmt = options.get('format', 'mp4')
            output_path = os.path.join(output_dir, f"{base_name}.{fmt}")
            success, result = await convert_format(input_path, fmt, output_path)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_audio':
            fmt = options.get('format', 'mp3')
            output_path = os.path.join(output_dir, f"{base_name}.{fmt}")
            success, result = await extract_audio(input_path, output_path, codec=fmt)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'remove_audio':
            success, result = await remove_audio(input_path, output_path)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_video':
            output_path = os.path.join(output_dir, f"{base_name}_video{ext}")
            success, result = await extract_video(input_path, output_path)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_subs':
            output_path = os.path.join(output_dir, f"{base_name}.srt")
            success, result = await extract_subtitles(input_path, output_path)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_thumb':
            output_path = os.path.join(output_dir, f"{base_name}_thumb.jpg")
            success, result = await extract_thumbnail(input_path, output_path)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_screenshots':
            output_path = os.path.join(output_dir, f"{base_name}_ss_%d.jpg")
            success, result = await extract_screenshots(input_path, output_path, count=5)
            if success:
                # Screenshots returns a list of files
                if isinstance(result, list) and result:
                    output_path = result[0]  # Use first screenshot for now
                else:
                    output_path = result
            else:
                error = result
        
        else:
            success = False
            error = f"Unknown operation: {operation}"
        
        if not success:
            await status_msg.edit_text(f"❌ Error: {error[:500]}")
            return
        
        # Check file size
        file_size = os.path.getsize(output_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Store output path for later upload
        user_data[user_id]['output_path'] = output_path
        user_data[user_id]['output_size'] = file_size
        
        # If file is larger than 2GB, show upload options
        if file_size_mb >= 2000:
            await status_msg.edit_text(
                f"<b>✅ Processing Complete!</b>\n\n"
                f"<b>📁 File:</b> <code>{os.path.basename(output_path)}</code>\n"
                f"<b>💾 Size:</b> {get_readable_file_size(file_size)}\n\n"
                f"<b>⚠️ File is larger than 2GB!</b>\n"
                f"Cannot upload to Telegram directly.\n\n"
                f"Choose upload destination:",
                reply_markup=after_process_menu(user_id, file_size_mb, GDRIVE_ENABLED)
            )
        else:
            # Show upload options for smaller files too
            await status_msg.edit_text(
                f"<b>✅ Processing Complete!</b>\n\n"
                f"<b>📁 File:</b> <code>{os.path.basename(output_path)}</code>\n"
                f"<b>💾 Size:</b> {get_readable_file_size(file_size)}\n\n"
                f"Choose upload destination:",
                reply_markup=after_process_menu(user_id, file_size_mb, GDRIVE_ENABLED)
            )
        
        # Cleanup input file
        try:
            os.remove(input_path)
        except:
            pass
        
    except Exception as e:
        LOGGER.error(f"Error processing: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:500]}")


# Google Drive upload callbacks
@bot.on_callback_query(filters.regex(r"^finalup_tg_"))
async def upload_telegram_callback(client: Client, query: CallbackQuery):
    """Upload processed file to Telegram"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data or 'output_path' not in user_data[user_id]:
        await query.answer("No file to upload!", show_alert=True)
        return
    
    output_path = user_data[user_id]['output_path']
    
    if not os.path.exists(output_path):
        await query.answer("File not found!", show_alert=True)
        return
    
    file_size = os.path.getsize(output_path)
    if file_size >= 2000 * 1024 * 1024:
        await query.answer("File too large for Telegram (>2GB)!", show_alert=True)
        return
    
    await query.answer("Uploading to Telegram...")
    status_msg = await query.message.edit_text("📤 Uploading to Telegram...")
    
    try:
        await upload_file(client, query.message.chat.id, output_path, status_msg)
        await status_msg.delete()
        
        # Cleanup
        try:
            os.remove(output_path)
            del user_data[user_id]['output_path']
        except:
            pass
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {str(e)[:200]}")


@bot.on_callback_query(filters.regex(r"^finalup_gdrive_"))
async def upload_gdrive_callback(client: Client, query: CallbackQuery):
    """Upload processed file to Google Drive"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if not GDRIVE_ENABLED:
        await query.answer("Google Drive is not configured!", show_alert=True)
        return
    
    if user_id not in user_data or 'output_path' not in user_data[user_id]:
        await query.answer("No file to upload!", show_alert=True)
        return
    
    output_path = user_data[user_id]['output_path']
    
    if not os.path.exists(output_path):
        await query.answer("File not found!", show_alert=True)
        return
    
    await query.answer("Uploading to Google Drive...")
    status_msg = await query.message.edit_text("☁️ Uploading to Google Drive...")
    
    try:
        gdrive = get_gdrive()
        if not gdrive.is_ready:
            init_gdrive()
            gdrive = get_gdrive()
        
        if not gdrive.is_ready:
            await status_msg.edit_text(
                "❌ Google Drive not configured!\n\n"
                "Please add a valid credentials.json file."
            )
            return
        
        # Progress callback
        async def progress_callback(percent, current, total):
            try:
                await status_msg.edit_text(
                    f"☁️ <b>Uploading to Google Drive</b>\n\n"
                    f"<b>Progress:</b> {percent:.1f}%\n"
                    f"<b>Uploaded:</b> {get_readable_file_size(current)} / {get_readable_file_size(total)}"
                )
            except:
                pass
        
        success, result = await gdrive.upload_file(
            output_path,
            folder_id=GDRIVE_FOLDER_ID if GDRIVE_FOLDER_ID else None,
            progress_callback=progress_callback
        )
        
        if success:
            await status_msg.edit_text(
                f"<b>✅ Uploaded to Google Drive!</b>\n\n"
                f"<b>📁 File:</b> <code>{result['name']}</code>\n"
                f"<b>💾 Size:</b> {get_readable_file_size(result['size'])}\n\n"
                f"<b>🔗 Link:</b> {result['link']}",
                disable_web_page_preview=True
            )
            
            # Cleanup
            try:
                os.remove(output_path)
                del user_data[user_id]['output_path']
            except:
                pass
        else:
            await status_msg.edit_text(f"❌ Upload failed: {result[:200]}")
            
    except Exception as e:
        LOGGER.error(f"GDrive upload error: {e}")
        await status_msg.edit_text(f"❌ Upload failed: {str(e)[:200]}")


@bot.on_callback_query(filters.regex(r"^cancel_upload_"))
async def cancel_upload_callback(client: Client, query: CallbackQuery):
    """Cancel upload and delete processed file"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    # Cleanup
    if user_id in user_data and 'output_path' in user_data[user_id]:
        try:
            os.remove(user_data[user_id]['output_path'])
            del user_data[user_id]['output_path']
        except:
            pass
    
    await query.message.delete()
    await query.answer("Cancelled and deleted!")

