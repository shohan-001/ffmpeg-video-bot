#!/usr/bin/env python3
"""Callback query handlers for inline buttons"""

import os
from types import SimpleNamespace
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from bot import (
    bot,
    OWNER_ID,
    DOWNLOAD_DIR,
    OUTPUT_DIR,
    LOGGER,
    user_data,
    GDRIVE_ENABLED,
    GDRIVE_FOLDER_ID,
    processing_queue,
)
from bot.keyboards.menus import (
    main_menu, encode_menu, preset_menu, resolution_menu,
    convert_menu, extract_menu, remove_menu, watermark_menu,
    watermark_position_menu, audio_format_menu, confirm_menu,
    close_button, speed_menu, rotate_menu, after_process_menu, stream_selection_menu,
    screenshot_count_menu, sample_duration_menu, sample_start_menu
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


@bot.on_callback_query(filters.regex(r"^ffcmd_"))
async def ffcmd_callback(client: Client, query: CallbackQuery):
    """Handle FFMPEG CMD"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
        
    user_data[user_id]['operation'] = 'ffmpeg_cmd'
    user_data[user_id]['waiting_for'] = 'ffmpeg_cmd'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>🎬 FFMPEG CMD</b>\n\n"
        "Send me the FFmpeg arguments.\n"
        "Example: <code>-c:v libx265 -crf 28 -c:a aac -b:a 128k</code>\n\n"
        "Input file is automatically handled.",
        reply_markup=back_and_close_button(user_id, f"main_{user_id}")
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^vidvid_"))
async def vidvid_callback(client: Client, query: CallbackQuery):
    """Handle Vid+Vid - Multi-video merge"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['operation'] = 'merge_video'
    user_data[user_id]['waiting_for'] = 'merge_videos'
    user_data[user_id]['merge_queue'] = []  # List to collect videos/URLs
    
    # Auto-add the first video if already downloaded
    first_video_name = "First video"
    first_video_count = 0
    if user_data[user_id].get('file_path') and os.path.exists(user_data[user_id].get('file_path', '')):
        first_video_name = user_data[user_id].get('file_name', 'First video')
        user_data[user_id]['merge_queue'].append({
            'type': 'file',
            'path': user_data[user_id]['file_path'],
            'name': first_video_name
        })
        first_video_count = 1
    elif user_data[user_id].get('message_id'):
        # Video not downloaded yet, add as telegram message
        first_video_name = user_data[user_id].get('file_name', 'First video')
        first_video_count = 1
        # We'll handle first video separately in multi_merge
    
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done - Start Merge", callback_data=f"merge_done_{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{user_id}")]
    ])
    
    first_note = f"\n<b>First video:</b> {first_video_name[:40]}" if first_video_count else ""
    
    await query.message.edit_text(
        f"<b>🎥 Multi-Video Merge</b>\n\n"
        f"Send me MORE videos or video URLs to merge.{first_note}\n\n"
        f"<b>Supported:</b>\n"
        f"• Telegram video files\n"
        f"• YouTube/yt-dlp supported URLs\n"
        f"• Direct video links\n\n"
        f"<b>Videos in queue:</b> {first_video_count} (+ videos you send)\n\n"
        f"Click <b>Done</b> when finished adding.",
        reply_markup=keyboard
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^merge_done_"))
async def merge_done_callback(client: Client, query: CallbackQuery):
    """Start merging collected videos"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        await query.answer("No session found!", show_alert=True)
        return
    
    merge_queue = user_data[user_id].get('merge_queue', [])
    
    if len(merge_queue) < 2:
        await query.answer("Need at least 2 videos to merge!", show_alert=True)
        return
    
    user_data[user_id]['waiting_for'] = None
    await query.answer("Starting merge...")
    await process_video(client, query, 'multi_merge', {'videos': merge_queue})


@bot.on_callback_query(filters.regex(r"^streamswap_"))
async def streamswap_callback(client: Client, query: CallbackQuery):
    """Handle StreamSwap"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>🔄 StreamSwap</b>\n\n"
        "Swapping video and audio streams via map...\n"
        "This is an automated 1-click operation.",
        reply_markup=confirm_menu(user_id, 'streamswap')
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^subintro_"))
async def subintro_callback(client: Client, query: CallbackQuery):
    """Handle Sub Intro"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['operation'] = 'sub_intro'
    user_data[user_id]['waiting_for'] = 'sub_intro_text'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>📜 Sub Intro</b>\n\n"
        "Send me the text to show as intro (5 seconds).\n"
        "It will be burned as subtitles.",
        reply_markup=back_and_close_button(user_id, f"main_{user_id}")
    )
    await query.answer()


# ... back_callback omitted (unchanged) ...

@bot.on_callback_query(filters.regex(r"^metadata_"))
async def metadata_callback(client: Client, query: CallbackQuery):
    """Handle MegaMetaData"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['operation'] = 'metadata'
    user_data[user_id]['waiting_for'] = 'metadata_input'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>📝 MegaMetaData</b>\n\n"
        "Send me the metadata in this format:\n\n"
        "<code>title: Your Title\n"
        "author: Author Name\n"
        "album: Album Name\n"
        "year: 2026</code>\n\n"
        "Or send just the title.",
        reply_markup=back_and_close_button(user_id, f"main_{user_id}")
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^encode_"))
async def encode_callback(client: Client, query: CallbackQuery):
    """Handle Encode menu"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['operation'] = 'encode'
    
    # Load encode settings from DB (if available) as authoritative source
    from bot.utils.db_handler import get_db
    db = get_db()
    db_settings = {}
    if db:
        try:
            db_settings = await db.get_user_settings(user_id)
        except Exception:
            db_settings = {}

    # Merge in-memory settings over DB defaults (so runtime tweaks are visible)
    runtime_settings = user_data[user_id].get('settings', {})
    settings = {**db_settings, **runtime_settings}
    
    await query.message.edit_text(
        "<b>⚙️ Encode Settings</b>\n\n"
        f"<b>Preset:</b> {settings.get('preset', 'medium')}\n"
        f"<b>CRF:</b> {settings.get('crf', 23)}\n"
        f"<b>Video Codec:</b> {settings.get('video_codec', 'libx264')}\n"
        f"<b>Audio Codec:</b> {settings.get('audio_codec', 'aac')}\n"
        f"<b>Resolution:</b> {settings.get('resolution', 'Original')}\n\n"
        "Select an option to change:",
        reply_markup=encode_menu(user_id, settings)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_preset_"))
async def preset_callback(client: Client, query: CallbackQuery):
    """Show preset selection menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    # Get current preset
    from bot.utils.db_handler import get_db
    db = get_db()
    current = "medium"
    
    if 'settings' in user_data.get(user_id, {}):
        current = user_data[user_id]['settings'].get('preset', 'medium')
    elif db:
        try:
            s = await db.get_user_settings(user_id)
            current = s.get('preset', 'medium')
        except: pass

    await query.message.edit_text(
        f"<b>📊 Select Encoding Preset</b>\nCurrent: {current}\n\n"
        "Faster = Lower quality\n"
        "Slower = Higher quality",
        reply_markup=preset_menu(user_id, current)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_crf_"))
async def crf_callback(client: Client, query: CallbackQuery):
    """Set CRF value"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['waiting_for'] = 'enc_crf'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>🎯 Set CRF Value</b>\n\n"
        "Send a value between 0-51.\n"
        "Lower = Better Quality (Larger size)\n"
        "Higher = Lower Quality (Smaller size)\n"
        "Default: 23 (libx264), 28 (libx265)",
        reply_markup=back_and_close_button(user_id, f"encode_{user_id}")
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_vcodec_"))
async def vcodec_callback(client: Client, query: CallbackQuery):
    """Set video codec"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['waiting_for'] = 'enc_vcodec'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>🎬 Set Video Codec</b>\n\n"
        "Send the codec name.\n"
        "Examples: <code>libx264</code>, <code>libx265</code>, <code>vp9</code>, <code>copy</code>",
        reply_markup=back_and_close_button(user_id, f"encode_{user_id}")
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_acodec_"))
async def acodec_callback(client: Client, query: CallbackQuery):
    """Set audio codec"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['waiting_for'] = 'enc_acodec'
    
    from bot.keyboards.menus import back_and_close_button
    await query.message.edit_text(
        "<b>🔊 Set Audio Codec</b>\n\n"
        "Send the codec name.\n"
        "Examples: <code>aac</code>, <code>libmp3lame</code>, <code>libopus</code>, <code>copy</code>",
        reply_markup=back_and_close_button(user_id, f"encode_{user_id}")
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_profile_"))
async def enc_profile_menu_callback(client: Client, query: CallbackQuery):
    """Show simple encoding profiles (maps to preset+CRF+codec)."""
    user_id = int(query.data.split("_")[2])

    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return

    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    buttons = [
        [
            InlineKeyboardButton("🎥 High Quality", callback_data=f"enc_prof_high_{user_id}"),
        ],
        [
            InlineKeyboardButton("⚖️ Balanced", callback_data=f"enc_prof_bal_{user_id}"),
        ],
        [
            InlineKeyboardButton("📦 Small Size", callback_data=f"enc_prof_small_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"encode_{user_id}"),
        ],
    ]

    await query.message.edit_text(
        "<b>🎛 Encoding Profiles</b>\n\n"
        "Choose a profile; you can still fine‑tune settings after:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_prof_"))
async def enc_profile_apply_callback(client: Client, query: CallbackQuery):
    """Apply selected encoding profile to settings and DB."""
    parts = query.data.split("_")
    profile_key = parts[2]  # high / bal / small
    user_id = int(parts[3])

    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return

    # Define simple profiles
    if profile_key == "high":
        profile = {"preset": "slow", "crf": 20, "video_codec": "libx264"}
    elif profile_key == "small":
        profile = {"preset": "slow", "crf": 30, "video_codec": "libx265"}
    else:  # balanced
        profile = {"preset": "medium", "crf": 23, "video_codec": "libx264"}

    # Update in-memory settings
    if user_id not in user_data:
        user_data[user_id] = {}
    settings = user_data[user_id].get("settings", {})
    settings.update(profile)
    user_data[user_id]["settings"] = settings

    # Persist to DB if available
    try:
        from bot.utils.db_handler import get_db
        db = get_db()
        if db:
            for k, v in profile.items():
                await db.update_setting(user_id, k, v)
    except Exception:
        pass

    await query.answer("Profile applied!")
    # Return to main encode menu to show updated values
    await encode_callback(client, query)


@bot.on_callback_query(filters.regex(r"^enc_fps_"))
async def fps_callback(client: Client, query: CallbackQuery):
    """Set FPS"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['waiting_for'] = 'enc_fps'
    
    await query.message.edit_text(
        "<b>🖼️ Set FPS</b>\n\n"
        "Send the target FPS (frames per second).\n"
        "Examples: <code>30</code>, <code>60</code>, <code>24</code>",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^enc_start_"))
async def encode_start_callback(client: Client, query: CallbackQuery):
    """Start encoding"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.answer("Starting encoding...")
    
    settings = user_data[user_id].get('settings', {})
    await process_video(client, query, 'encode', settings)


@bot.on_callback_query(filters.regex(r"^wm_pos_"))
async def wm_pos_callback(client: Client, query: CallbackQuery):
    """Show watermark position menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>📍 Select Watermark Position</b>",
        reply_markup=watermark_position_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^wmpos_"))
async def set_wm_pos_callback(client: Client, query: CallbackQuery):
    """Set watermark position"""
    parts = query.data.split("_")
    pos = f"{parts[1]}_{parts[2]}" if len(parts) > 3 else parts[1] # handle top_left etc.
    user_id = int(parts[-1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if 'watermark_settings' not in user_data[user_id]:
        user_data[user_id]['watermark_settings'] = {}
        
    user_data[user_id]['watermark_settings']['position'] = pos
    await query.answer(f"Position set to: {pos}")
    
    # Return to watermark menu
    await watermark_callback(client, query)


@bot.on_callback_query(filters.regex(r"^wm_opacity_"))
async def wm_opacity_callback(client: Client, query: CallbackQuery):
    """Set watermark opacity"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    user_data[user_id]['waiting_for'] = 'wm_opacity'
    
    await query.message.edit_text(
        "<b>🔍 Set Opacity</b>\n\n"
        "Send a value between 0.1 and 1.0.\n"
        "Example: 0.5 (50% transparent)",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^wm_apply_"))
async def wm_apply_callback(client: Client, query: CallbackQuery):
    """Apply watermark"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    # Check if we have watermark input
    if 'watermark_settings' not in user_data[user_id]:
        await query.answer("Configure watermark first!", show_alert=True)
        return
        
    await query.answer("Applying watermark...")
    
    settings = user_data[user_id].get('watermark_settings', {})
    await process_video(client, query, 'watermark', settings)


@bot.on_callback_query(filters.regex(r"^confirm_"))
async def confirm_callback(client: Client, query: CallbackQuery):
    """Handle confirmation"""
    parts = query.data.split("_")
    action = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer("Confirmed!")
    
    if action == 'streamswap':
        await process_video(client, query, 'streamswap', {})
    else:
        await query.answer("Unknown action", show_alert=True)


@bot.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client: Client, query: CallbackQuery):
    """Generic cancel/close"""
    await close_callback(client, query)


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
    
    # Get current resolution
    from bot.utils.db_handler import get_db
    db = get_db()
    current = "Original"
    
    # Check runtime first, then DB
    if 'settings' in user_data.get(user_id, {}):
        current = user_data[user_id]['settings'].get('resolution', 'Original')
    elif db:
        try:
            s = await db.get_user_settings(user_id)
            current = s.get('resolution', 'Original')
        except: pass

    await query.message.edit_text(
        f"<b>📐 Select Resolution</b>\nCurrent: {current}",
        reply_markup=resolution_menu(user_id, current)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^res_"))
async def set_resolution_callback(client: Client, query: CallbackQuery):
    """Set resolution"""
    parts = query.data.split("_")
    res = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    if 'settings' not in user_data[user_id]:
        user_data[user_id]['settings'] = {}
    
    user_data[user_id]['settings']['resolution'] = res
    
    # Persist to DB
    from bot.utils.db_handler import get_db
    db = get_db()
    if db:
        await db.update_setting(user_id, 'resolution', res)
        
    await query.answer(f"Resolution set to: {res}")
    
    # Return to encode menu
    await encode_callback(client, query)


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
    """Show audio format selection (and stream selection if needed)"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    # Check session
    if user_id not in user_data:
        await query.answer("Session expired", show_alert=True)
        return

    # Ensure file downloaded
    file_path = user_data[user_id].get('file_path')
    if not file_path or not os.path.exists(file_path):
        status_msg = await query.message.edit_text("⏳ Downloading video to analyze streams...")
        orig_msg_id = user_data[user_id].get('message_id')
        if not orig_msg_id:
            await status_msg.edit_text("❌ Original video lost!")
            return
        
        try:
            video_msg = await client.get_messages(query.message.chat.id, orig_msg_id)
            if not video_msg:
                 await status_msg.edit_text("❌ Video message deleted!")
                 return
            file_path = await download_file(video_msg, status_msg)
            user_data[user_id]['file_path'] = file_path
        except Exception as e:
            await status_msg.edit_text(f"❌ Download failed: {e}")
            return

    # Analyze streams
    ffmpeg = FFmpeg(file_path)
    streams = await ffmpeg.get_streams()
    audios = streams.get('audio', [])
    
    if not audios:
        await query.message.edit_text("❌ No audio streams found!", reply_markup=extract_menu(user_id))
        return
        
    if len(audios) == 1:
        # Just one, set default and show format menu
        user_data[user_id]['selected_audio_stream'] = 0
        await query.message.edit_text(
            "<b>🔊 Extract Audio</b>\n\n"
            "Select output format:",
            reply_markup=audio_format_menu(user_id)
        )
        await query.answer()
        return
        
    # Multiple -> Show stream menu
    await query.message.edit_text(
        "<b>🔊 Select Audio Stream</b>",
        reply_markup=stream_selection_menu(user_id, audios, 'audio')
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^selaud_"))
async def aud_select_callback(client: Client, query: CallbackQuery):
    """Handle audio stream selection"""
    parts = query.data.split("_")
    idx = int(parts[1])
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    user_data[user_id]['selected_audio_stream'] = idx
    
    await query.message.edit_text(
        f"<b>🔊 Extract Audio (Stream #{idx+1})</b>\n\n"
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
    
    # Get selected stream index (default 0)
    idx = user_data[user_id].get('selected_audio_stream', 0)
    
    await process_video(client, query, 'extract_audio', {'format': fmt, 'stream_index': idx})


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
    
    # Check if we have file info
    if user_id not in user_data:
        await query.answer("Session expired. Send video again.", show_alert=True)
        return
    
    # Ensure file is downloaded for analysis
    file_path = user_data[user_id].get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        status_msg = await query.message.edit_text("⏳ Downloading video to analyze streams...")
        
        orig_msg_id = user_data[user_id].get('message_id')
        if not orig_msg_id:
            await status_msg.edit_text("❌ Original video found!")
            return
            
        try:
            video_msg = await client.get_messages(query.message.chat.id, orig_msg_id)
            if not video_msg:
                await status_msg.edit_text("❌ Video message deleted!")
                return
                
            file_path = await download_file(video_msg, status_msg)
            user_data[user_id]['file_path'] = file_path
        except Exception as e:
            await status_msg.edit_text(f"❌ Download failed: {e}")
            return
    
    # Analyze streams
    ffmpeg = FFmpeg(file_path)
    streams = await ffmpeg.get_streams()
    subs = streams.get('subtitle', [])
    
    if not subs:
        await query.message.edit_text("❌ No subtitle streams found!", reply_markup=extract_menu(user_id))
        return
        
    if len(subs) == 1:
        # Just one, extract it
        await query.answer("Extracting subtitles...")
        await process_video(client, query, 'extract_subs', {'stream_index': 0})
        return
        
    # Multiple -> Show menu
    await query.message.edit_text(
        "<b>📝 Select Subtitle Stream</b>",
        reply_markup=stream_selection_menu(user_id, subs, 'subtitle')
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^selsub_"))
async def sub_select_callback(client: Client, query: CallbackQuery):
    """Handle subtitle stream selection"""
    parts = query.data.split("_")
    idx = int(parts[1])
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer(f"Extracting stream #{idx+1}...")
    await process_video(client, query, 'extract_subs', {'stream_index': idx})


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
    """Show screenshot count menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>📸 Screenshots</b>\n\nHow many screenshots do you want?",
        reply_markup=screenshot_count_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^sscnt_"))
async def screenshot_count_callback(client: Client, query: CallbackQuery):
    """Handle screenshot count selection"""
    parts = query.data.split("_")
    val = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    if val == 'custom':
        user_data[user_id]['waiting_for'] = 'ss_count'
        await query.message.edit_text("✍️ Enter number of screenshots (e.g. 15):")
        await query.answer()
        return
        
    count = int(val)
    await query.answer(f"Generating {count} screenshots...")
    await process_video(client, query, 'extract_screenshots', {'count': count})


@bot.on_callback_query(filters.regex(r"^ext_sample_"))
async def sample_video_callback(client: Client, query: CallbackQuery):
    """Show sample video menu"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
    
    await query.message.edit_text(
        "<b>🎞️ Sample Video</b>\n\nSelect duration:",
        reply_markup=sample_duration_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^sample_"))
async def sample_duration_callback(client: Client, query: CallbackQuery):
    """Handle sample duration selection"""
    parts = query.data.split("_")
    val = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    if val == 'custom':
        user_data[user_id]['waiting_for'] = 'sample_duration'
        await query.message.edit_text("✍️ Enter duration in seconds (e.g. 45):")
        await query.answer()
        return

    duration = int(val)
    user_data[user_id]['sample_duration'] = duration
    
    # Show start menu
    await query.message.edit_text(
        f"✅ Duration: {duration}s\n\nSelect start time:",
        reply_markup=sample_start_menu(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^samplestart_"))
async def sample_start_callback(client: Client, query: CallbackQuery):
    """Handle sample start selection"""
    parts = query.data.split("_")
    val = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    if val == 'custom':
        user_data[user_id]['waiting_for'] = 'sample_start'
        await query.message.edit_text("✍️ Enter start time (e.g. 00:05:30 or 120):")
        await query.answer()
        return
        
    # Random
    duration = user_data[user_id].get('sample_duration', 30)
    await query.answer("Generating sample with random start...")
    await process_video(client, query, 'generate_sample', {'duration': duration, 'start': 'random'})


@bot.on_callback_query(filters.regex(r"^speed_"))
async def speed_callback(client: Client, query: CallbackQuery):
    """Handle Speed menu and selection"""
    parts = query.data.split("_")
    
    # Check if menu request or selection
    if len(parts) == 2:
        # Show Speed Menu
        user_id = int(parts[1])
        if query.from_user.id != user_id:
            await query.answer("Not your button!", show_alert=True)
            return
            
        await query.message.edit_text(
            "<b>⏩ Select Speed</b>\n\n"
            "Values < 1.0 slow down\n"
            "Values > 1.0 speed up",
            reply_markup=speed_menu(user_id)
        )
        await query.answer()
        return

    # Selection: speed_{value}_{user_id}
    speed = float(parts[1])
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer(f"Setting speed to {speed}x...")
    await process_video(client, query, 'speed', {'speed': speed})


@bot.on_callback_query(filters.regex(r"^rotate_"))
async def rotate_callback(client: Client, query: CallbackQuery):
    """Handle Rotate menu and selection"""
    parts = query.data.split("_")
    
    # Check if menu request (rotate_uid)
    if len(parts) == 2:
        user_id = int(parts[1])
        if query.from_user.id != user_id:
            await query.answer("Not your button!", show_alert=True)
            return
            
        await query.message.edit_text(
            "<b>🔄 Select Rotation</b>",
            reply_markup=rotate_menu(user_id)
        )
        await query.answer()
        return
        
    # Selection: rotate_{val}_{uid}
    val = parts[1]
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer(f"Rotating {val}...")
    await process_video(client, query, 'rotate', {'rotation': val})


@bot.on_callback_query(filters.regex(r"^flip_"))
async def flip_callback(client: Client, query: CallbackQuery):
    """Handle Flip actions"""
    parts = query.data.split("_")
    val = f"flip_{parts[1]}" # flip_h or flip_v
    user_id = int(parts[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer(f"Flipping {parts[1]}...")
    await process_video(client, query, 'rotate', {'rotation': val})


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


# Main processing function with simple queue support
async def process_video(
    client: Client,
    query: CallbackQuery,
    operation: str,
    options: dict,
    queued: bool = False,
):
    """Process video with specified operation (supports per-user queue)"""
    user_id = query.from_user.id
    
    if user_id not in user_data:
        await query.message.edit_text("❌ No video found. Send a video first.")
        return

    # Initialize queue for user
    if user_id not in processing_queue:
        processing_queue[user_id] = []
    
    # If this is a fresh request and user already has an active task, enqueue it
    if not queued and 'progress' in user_data[user_id] and not user_data[user_id]['progress'].cancelled:
        from bot import MAX_QUEUE_PER_USER
        # Enforce simple per-user queue cap
        if len(processing_queue[user_id]) >= MAX_QUEUE_PER_USER:
            try:
                await query.answer("⚠️ Your queue is full. Please wait for current tasks to finish.", show_alert=True)
            except Exception:
                pass
            return

        processing_queue[user_id].append(
            {
                "operation": operation,
                "options": options or {},
            }
        )
        position = len(processing_queue[user_id])
        # Notify user that task has been queued
        try:
            await query.answer(f"Queued at position #{position}. It will start automatically.", show_alert=True)
        except Exception:
            pass
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
        
        # Check if file already downloaded
        input_path = user_data[user_id].get('file_path')
        if not input_path or not os.path.exists(input_path):
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
        progress = FFmpegProgress(status_msg, duration, f"Processing ({operation})", filename=os.path.basename(input_path))
        
        await status_msg.edit_text(f"⚙️ Processing: {operation}...")
        
        # Execute operation
        success = False
        error = ""
        
        if operation == 'convert':
            fmt = options.get('format', 'mp4')
            output_path = os.path.join(output_dir, f"{base_name}.{fmt}")
            success, result = await convert_format(input_path, fmt, output_path, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_audio':
            fmt = options.get('format', 'mp3')
            idx = int(options.get('stream_index', 0))
            output_path = os.path.join(output_dir, f"{base_name}_track{idx}.{fmt}")
            success, result = await extract_audio(input_path, output_path, stream_index=idx, codec=fmt, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'remove_audio':
            success, result = await remove_audio(input_path, output_path, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_video':
            idx = int(options.get('stream_index', 0))
            output_path = os.path.join(output_dir, f"{base_name}_video{idx}{ext}")
            success, result = await extract_video(input_path, output_path, stream_index=idx, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'extract_subs':
            idx = int(options.get('stream_index', 0))
            output_path = os.path.join(output_dir, f"{base_name}_track{idx}.srt")
            success, result = await extract_subtitles(input_path, output_path, stream_index=idx, progress_callback=progress.update, duration=duration)
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
            count = int(options.get('count', 5))
            
            # Use specific dir to avoid clutter
            ss_dir = os.path.join(output_dir, f"screenshots_{user_id}")
            success, result = await extract_screenshots(input_path, ss_dir, count=count)
            
            if success:
                # result is list of paths
                # Return list directly for Media Group upload
                output_path = result
            else:
                error = "Failed to extract screenshots"

        elif operation == 'generate_sample':
            duration = int(options.get('duration', 30))
            start_opt = options.get('start', 'random')
            
            start = "0"
            if start_opt == 'random':
                # Get duration
                ff = FFmpeg(input_path)
                total = await ff.get_duration()
                
                import random
                if total > duration:
                    # Random start
                    start_sec = random.randint(0, int(total - duration))
                    start = str(start_sec)
            else:
                start = str(start_opt)
                
            output_path = os.path.join(output_dir, f"{base_name}_sample_{duration}s{ext}")
            
            # Use trim_video
            success, result = await trim_video(input_path, output_path, start_time=start, duration=str(duration))
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'metadata':
            metadata = options.get('metadata', {})
            success, result = await edit_metadata(input_path, output_path, metadata)
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'ffmpeg_cmd':
            args = options.get('args', '')
            success, result = await execute_custom_command(input_path, args, output_path)
            if success:
                pass # output_path is already set
            else:
                error = result

        elif operation == 'trim':
            start = options.get('start')
            end = options.get('end')
            success, result = await trim_video(input_path, output_path, start, end)
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'rename':
            new_name = options.get('new_name', 'video')
            new_path = os.path.join(output_dir, f"{new_name}{ext}")
            try:
                os.rename(input_path, new_path)
                output_path = new_path
                success = True
            except Exception as e:
                success = False
                error = str(e)

        elif operation == 'sub_intro':
            text = options.get('text', '')
            success, result = await add_subtitle_intro(input_path, text, output_path, duration=5)
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'streamswap':
            success, result = await swap_streams(input_path, output_path, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'merge_video':
            # Need to download second video
            msg = user_data[user_id].get('second_video_message')
            if not msg:
                success = False
                error = "Second video not found"
            else:
                await status_msg.edit_text("📥 Downloading second video...")
                second_path = await download_file(msg, status_msg)
                
                await status_msg.edit_text("⚙️ Merging videos...")
                success, result = await merge_videos(input_path, second_path, output_path, progress_callback=progress.update, duration=duration)
                
                # Cleanup second video
                try:
                    os.remove(second_path)
                except:
                    pass
                    
                if success:
                    output_path = result
                else:
                    error = result

        elif operation == 'multi_merge':
            # Multi-video merge with URL support
            videos = options.get('videos', [])
            
            # Check length of queue (includes first video if added)
            if len(videos) < 1:
                success = False
                error = "No videos to merge"
            else:
                video_paths = []
                
                # Check if first video needs to be added (implicit)
                first_video_path = input_path if os.path.exists(input_path) else None
                
                # Iterate queue and resolve paths
                for i, video in enumerate(videos):
                    await status_msg.edit_text(f"📥 Preparing video {i+1}/{len(videos)}...")
                    
                    if video['type'] == 'file':
                        # Already local file (first video)
                        if os.path.exists(video['path']):
                            video_paths.append(video['path'])
                    elif video['type'] == 'telegram':
                        path = await download_file(video['message'], status_msg)
                        video_paths.append(path)
                    elif video['type'] == 'url':
                        # Download URL using yt-dlp with fallback to HTTP
                        from bot.utils.ytdlp_handler import download_with_ytdlp
                        url_output_dir = os.path.join(OUTPUT_DIR, str(user_id))
                        os.makedirs(url_output_dir, exist_ok=True)
                        
                        success_dl, result_dl = await download_with_ytdlp(
                            video['url'], url_output_dir, user_id=user_id
                        )
                        
                        if not success_dl:
                            # Fallback to direct HTTP download
                            from bot.utils.helpers import download_http_file
                            await status_msg.edit_text(f"⚠️ yt-dlp failed, trying direct download...")
                            result_dl = await download_http_file(video['url'], url_output_dir, status_msg, user_id)
                            success_dl = bool(result_dl)
                        
                        if success_dl:
                            video_paths.append(result_dl)
                        else:
                            await status_msg.edit_text(f"❌ Failed to download: {video['url'][:50]}")
                            # Cleanup downloaded paths
                            for p in video_paths:
                                if p and os.path.exists(p) and p != first_video_path:
                                    try: os.remove(p)
                                    except: pass
                            return
                
                # If Input Path (first video) is NOT in video_paths, prepend it
                # This handles cases where queue didn't include it explicitly
                if first_video_path:
                    # Normalize paths for comparison
                    norm_first = os.path.normpath(first_video_path)
                    if not any(os.path.normpath(p) == norm_first for p in video_paths):
                        video_paths.insert(0, first_video_path)
                
                if len(video_paths) < 2:
                    success = False
                    error = "Not enough videos (need at least 2)"
                    # Cleanup usage if we downloaded extra things but failed count check
                    for p in video_paths:
                        if p and os.path.exists(p) and p != first_video_path:
                            try: os.remove(p)
                            except: pass
                
                if len(video_paths) < 2:
                    success = False
                    error = "Not enough videos downloaded"
                else:
                    # Merge videos one by one
                    await status_msg.edit_text(f"⚙️ Merging {len(video_paths)} videos...")
                    
                    current_path = video_paths[0]
                    for i in range(1, len(video_paths)):
                        merge_output = os.path.join(output_dir, f"merged_{i}.mp4")
                        success, result = await merge_videos(
                            current_path, video_paths[i], merge_output,
                            progress_callback=progress.update, duration=duration
                        )
                        
                        if not success:
                            error = result
                            break
                        
                        # Cleanup previous merged file (if not first)
                        if i > 1 and os.path.exists(current_path):
                            try: os.remove(current_path)
                            except: pass
                        
                        current_path = result
                    
                    if success:
                        output_path = current_path
                
                # Cleanup downloaded videos (except input)
                for p in video_paths:
                    if p and os.path.exists(p) and p != input_path and p != output_path:
                        try: os.remove(p)
                        except: pass

        elif operation == 'watermark':
            # Text or Image?
            wm_text = options.pop('text', None)  # Use pop to remove from options
            if wm_text:
                success, result = await add_text_watermark(input_path, wm_text, output_path, progress_callback=progress.update, duration=duration, **options)
            else:
                # Image
                # Need to download image if not local (but wait, how do we get image?)
                # file_handler handles watermark_image -> stores message
                msg = user_data[user_id].get('watermark_message')
                if msg:
                     # Download image
                     wm_path = await download_file(msg, status_msg)
                     success, result = await add_image_watermark(input_path, wm_path, output_path, progress_callback=progress.update, duration=duration, **options)
                     try:
                         os.remove(wm_path)
                     except:
                         pass
                else:
                    success = False
                    error = "Watermark image/text not provided"
            
            if success:
                output_path = result
            else:
                error = result

        elif operation in ['add_subtitle', 'hardsub']:
            # Need subtitle file
            msg = user_data[user_id].get('subtitle_message')
            if not msg:
                success = False
                error = "Subtitle file not found"
            else:
                await status_msg.edit_text("📥 Downloading subtitles...")
                sub_path = await download_file(msg, status_msg)
                
                await status_msg.edit_text("⚙️ Adding subtitles...")
                if operation == 'hardsub':
                    success, result = await burn_subtitles(input_path, sub_path, output_path, progress_callback=progress.update, duration=duration)
                else:
                    success, result = await add_subtitle_to_video(input_path, sub_path, output_path, progress_callback=progress.update, duration=duration)
                
                try:
                    os.remove(sub_path)
                except:
                    pass
                    
                if success:
                    output_path = result
                else:
                    error = result

        elif operation == 'add_audio':
            # Need audio file
            msg = user_data[user_id].get('audio_message')
            if not msg:
                success = False
                error = "Audio file not found"
            else:
                await status_msg.edit_text("📥 Downloading audio...")
                aud_path = await download_file(msg, status_msg)
                
                await status_msg.edit_text("⚙️ Adding audio...")
                success, result = await add_audio_to_video(input_path, aud_path, output_path, progress_callback=progress.update, duration=duration)
                
                try:
                    os.remove(aud_path)
                except:
                    pass
                    
                if success:
                    output_path = result
                else:
                    error = result

        elif operation == 'speed':
            speed = options.get('speed', 1.0)
            success, result = await change_speed(input_path, output_path, speed, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'rotate':
            rotation = options.get('rotation', 'right')
            success, result = await rotate_video(input_path, output_path, rotation, progress_callback=progress.update, duration=duration)
            if success:
                output_path = result
            else:
                error = result
        
        elif operation == 'encode':
            # Use encode wrapper with progress reporting
            success, result = await encode_video(
                input_path,
                output_path,
                **options,
                progress_callback=progress.update
            )
            if success:
                output_path = result
            else:
                error = result

        elif operation == 'convert':
            fmt = options.get('format', 'mp4')
            # convert_format supports progress & duration
            success, result = await convert_format(
                input_path,
                fmt,
                output_path,
                progress_callback=progress.update,
                duration=duration
            )
            if success:
                output_path = result
            else:
                error = result
        
        if not success:
            await status_msg.edit_text(f"❌ Error: {error[:500]}")
            return
        
        # Check file size
        if isinstance(output_path, list):
            file_size = sum(os.path.getsize(f) for f in output_path)
            display_name = f"Screenshots ({len(output_path)} photos)"
        else:
            file_size = os.path.getsize(output_path)
            display_name = f"<code>{os.path.basename(output_path)}</code>"
            
        file_size_mb = file_size / (1024 * 1024)
        
        # Store output path for later upload
        user_data[user_id]['output_path'] = output_path
        user_data[user_id]['output_size'] = file_size
        
        # If file is larger than 2GB, show upload options
        # For list, we might rely on Telegram limits, but usually screenshots are small
        if file_size_mb >= 2000:
            msg_text = (
                f"<b>✅ Processing Complete!</b>\n\n"
                f"<b>📁 File:</b> {display_name}\n"
                f"<b>💾 Size:</b> {get_readable_file_size(file_size)}\n\n"
                f"<b>⚠️ Total size > 2GB!</b>\n"
                f"Cannot upload to Telegram directly.\n\n"
                f"Choose upload destination:"
            )
        else:
            # Show upload options for smaller files too
            msg_text = (
                f"<b>✅ Processing Complete!</b>\n\n"
                f"<b>📁 File:</b> {display_name}\n"
                f"<b>💾 Size:</b> {get_readable_file_size(file_size)}\n\n"
                f"Choose upload destination:"
            )
            
        await status_msg.edit_text(
            msg_text,
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
    finally:
        # If there are queued tasks for this user, start the next one
        if processing_queue.get(user_id):
            next_task = processing_queue[user_id].pop(0)
            
            # Build a minimal fake query object reusing the same message & user
            fake_query = SimpleNamespace(
                message=status_msg,
                from_user=query.from_user,
            )
            await process_video(
                client,
                fake_query,
                next_task["operation"],
                next_task.get("options", {}),
                queued=True,
            )


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
    
    # Verify files
    if isinstance(output_path, list):
        if not all(os.path.exists(f) for f in output_path):
            await query.answer("Some files not found!", show_alert=True)
            return
        total_size = sum(os.path.getsize(f) for f in output_path)
    else:
        if not os.path.exists(output_path):
            await query.answer("File not found!", show_alert=True)
            return
        total_size = os.path.getsize(output_path)
    
    if total_size >= 2000 * 1024 * 1024:
        await query.answer("Total size too large for Telegram (>2GB)!", show_alert=True)
        return
    
    await query.answer("Uploading to Telegram...")
    status_msg = await query.message.edit_text("📤 Uploading to Telegram...")
    
    try:
        await upload_file(client, query.message.chat.id, output_path, status_msg, user_id=user_id)
        await status_msg.delete()
        
        # Cleanup
        try:
            if isinstance(output_path, list):
                for f in output_path: 
                    os.remove(f)
                # Try to remove the screenshots directory
                if output_path:
                    try:
                        os.rmdir(os.path.dirname(output_path[0]))
                    except:
                        pass
            else:
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
    real_upload_path = output_path
    is_zip = False
    
    # Handle list (Screenshots) -> Zip for GDrive
    if isinstance(output_path, list):
        if not output_path or not os.path.exists(output_path[0]):
             await query.answer("Files not found!", show_alert=True)
             return
             
        try:
            import zipfile
            dir_path = os.path.dirname(output_path[0])
            zip_path = os.path.join(dir_path, "screenshots.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for f in output_path:
                     if os.path.exists(f):
                        zf.write(f, os.path.basename(f))
            
            real_upload_path = zip_path
            is_zip = True
        except Exception as e:
            await query.answer(f"Zip failed: {e}", show_alert=True)
            return

    if not os.path.exists(real_upload_path):
        await query.answer("File not found!", show_alert=True)
        return
    
    await query.answer("Uploading to Google Drive...")
    status_msg = await query.message.edit_text("☁️ Uploading to Google Drive...")
    
    try:
        gdrive = get_gdrive()
        if not gdrive.is_ready:
            await gdrive.initialize()
        
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
        
        # Determine Folder ID (DB > Env)
        from bot import GDRIVE_FOLDER_ID
        from bot.utils.db_handler import get_db
        db = get_db()
        db_folder_id = await db.get_gdrive_folder_id()
        folder_id_to_use = db_folder_id if db_folder_id else GDRIVE_FOLDER_ID

        success, result = await gdrive.upload_file(
            real_upload_path,
            folder_id=folder_id_to_use if folder_id_to_use else None,
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
                if is_zip:
                    os.remove(real_upload_path) # remove zip
                    for f in output_path: # remove originals
                        os.remove(f)
                    try:
                        os.rmdir(os.path.dirname(output_path[0]))
                    except:
                        pass
                else:
                    os.remove(output_path)
                
                del user_data[user_id]['output_path']
            except:
                pass
        else:
            import html
            await status_msg.edit_text(f"❌ Upload failed: {html.escape(str(result))[:300]}")
            
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
        path_var = user_data[user_id]['output_path']
        try:
            if isinstance(path_var, list):
                for f in path_var: 
                    try: os.remove(f)
                    except: pass
                # Clean dir
                if path_var:
                    try: os.rmdir(os.path.dirname(path_var[0]))
                    except: pass
            else:
                os.remove(path_var)
            del user_data[user_id]['output_path']
        except:
            pass
    
    await query.message.delete()
    await query.answer("Cancelled and deleted!")


@bot.on_callback_query(filters.regex(r"^finalup_default_"))
async def upload_default_callback(client: Client, query: CallbackQuery):
    """Upload using user's default destination (Telegram or Google Drive)."""
    user_id = int(query.data.split("_")[2])

    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return

    from bot.utils.db_handler import get_db
    db = get_db()
    dest = "telegram"
    if db:
        try:
            dest = await db.get_default_destination(user_id)
        except Exception:
            dest = "telegram"

    # Delegate to the appropriate existing handler
    if dest == "gdrive":
        await upload_gdrive_callback(client, query)
    else:
        await upload_telegram_callback(client, query)

@bot.on_callback_query(filters.regex(r"^open_settings$"))
@bot.on_callback_query(filters.regex(r"^back_to_main_settings$"))
async def open_settings_callback(client: Client, query: CallbackQuery):
    """Open main settings menu"""
    from bot.keyboards.settings_menu import open_settings
    await query.message.edit_text(
        "<b>⚙️ Settings Menu</b>",
        reply_markup=await open_settings(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^set_video_codec$"))
async def set_video_codec_callback(client: Client, query: CallbackQuery):
    """Open video settings"""
    from bot.keyboards.settings_menu import video_settings_menu
    await query.message.edit_text(
        "<b>📹 Video Settings</b>\nToggle HEVC (x265) on/off.",
        reply_markup=await video_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^toggle_hevc$"))
async def toggle_hevc_callback(client: Client, query: CallbackQuery):
    """Toggle HEVC setting"""
    from bot.utils.db_handler import get_db
    from bot.keyboards.settings_menu import video_settings_menu
    
    db = get_db()
    current = await db.get_hevc(query.from_user.id)
    await db.set_hevc(query.from_user.id, not current)
    
    await query.message.edit_reply_markup(
        reply_markup=await video_settings_menu(query.from_user.id)
    )
    await query.answer(f"HEVC {'Enabled' if not current else 'Disabled'}!")

@bot.on_callback_query(filters.regex(r"^set_resolution$"))
async def set_resolution_menu_callback(client: Client, query: CallbackQuery):
    """Open resolution menu"""
    from bot.keyboards.settings_menu import resolution_settings_menu
    await query.message.edit_text(
        "<b>🖥 Resolution Settings</b>\nSelect target resolution.",
        reply_markup=await resolution_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^set_res_"))
async def set_resolution_val_callback(client: Client, query: CallbackQuery):
    """Set resolution value"""
    res = query.data.split("_")[2]
    from bot.keyboards.settings_menu import resolution_settings_menu
    from bot.utils.db_handler import get_db
    
    db = get_db()
    await db.set_resolution(query.from_user.id, res)
    
    await query.message.edit_reply_markup(
        reply_markup=await resolution_settings_menu(query.from_user.id)
    )
    await query.answer(f"Resolution set to {res}")

@bot.on_callback_query(filters.regex(r"^open_audio_settings$"))
async def open_audio_settings_callback(client: Client, query: CallbackQuery):
    """Open audio settings"""
    from bot.keyboards.settings_menu import audio_settings_menu
    await query.message.edit_text(
        "<b>🔊 Audio Settings</b>",
        reply_markup=await audio_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^close_settings$"))
async def close_settings_callback(client: Client, query: CallbackQuery):
    await query.message.delete()
@bot.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client: Client, query: CallbackQuery):
    """Handle Rename button (Main Menu)"""
    user_id = int(query.data.split("_")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['operation'] = 'rename'
    user_data[user_id]['waiting_for'] = 'new_filename'
    
    await query.message.edit_text(
        "<b>✏️ Rename File</b>\n\n"
        "Send me the new filename (with extension).\n"
        "Example: <code>my_video.mp4</code>",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^final_rename_"))
async def final_rename_callback(client: Client, query: CallbackQuery):
    """Handle Rename button (After Process)"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    user_data[user_id]['operation'] = 'final_rename'
    user_data[user_id]['waiting_for'] = 'final_rename_input'
    
    await query.message.edit_text(
        "<b>✏️ Rename Output</b>\n\n"
        "Send me the new filename for the processed video.\n"
        "Example: <code>encoded_video.mkv</code>",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^final_zip_"))
async def final_zip_callback(client: Client, query: CallbackQuery):
    """Handle Zip & Upload (After Process)"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    await query.answer("Zipping and uploading...")
    
    # Trigger final processing with ZIP flag
    # We can reuse the 'upload_to_telegram' flow but wrap it
    if 'output_path' not in user_data[user_id]:
        await query.answer("File not found!", show_alert=True)
        return
        
    output_path = user_data[user_id]['output_path']
    new_path = output_path + ".zip"
    
    status_msg = await query.message.edit_text("⏳ Zipping file...")
    
    try:
        from bot.utils.archive import create_archive
        zip_path = await create_archive(output_path, new_path, "zip")
        
        if zip_path:
            # Update output_path to point to zip
            user_data[user_id]['output_path'] = zip_path
            # Proceed to upload
            from bot.handlers.file_handler import upload_processed_file
            await upload_processed_file(client, user_id, status_msg, "telegram") # Defaulting to Telegram
        else:
            await status_msg.edit_text("❌ Zipping failed.")
            
    except Exception as e:
         await status_msg.edit_text(f"❌ Error: {e}")


@bot.on_callback_query(filters.regex(r"^set_thumb_"))
async def set_thumb_callback(client: Client, query: CallbackQuery):
    """Handle Set Thumbnail"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['waiting_for'] = 'set_thumbnail'
    
    await query.message.edit_text(
        "🖼️ <b>Send me a photo to set as your custom thumbnail.</b>\n"
        "Sending a photo now will save it as your thumbnail.",
        reply_markup=close_button(user_id)
    )
    await query.answer()


@bot.on_callback_query(filters.regex(r"^del_thumb_"))
async def del_thumb_callback(client: Client, query: CallbackQuery):
    """Handle Delete Thumbnail"""
    user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != user_id:
        await query.answer("Not your button!", show_alert=True)
        return
        
    from bot.utils.db_handler import get_db
    db = get_db()
    await db.set_thumbnail(user_id, None)
    
    await query.message.edit_text("✅ <b>Thumbnail deleted!</b>")
    await query.answer()

# --- Missing Settings Handlers ---

@bot.on_callback_query(filters.regex(r"^open_subtitle_settings$"))
async def open_subtitle_settings_callback(client: Client, query: CallbackQuery):
    """Open subtitle settings"""
    from bot.keyboards.settings_menu import subtitle_settings_menu
    await query.message.edit_text(
        "<b>📜 Subtitle Settings</b>",
        reply_markup=await subtitle_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^open_watermark_settings$"))
async def open_watermark_settings_callback(client: Client, query: CallbackQuery):
    """Open watermark settings"""
    from bot.keyboards.settings_menu import watermark_settings_menu
    await query.message.edit_text(
        "<b>©️ Watermark Settings</b>",
        reply_markup=await watermark_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^open_advanced_settings$"))
async def open_advanced_settings_callback(client: Client, query: CallbackQuery):
    """Open advanced settings"""
    from bot.keyboards.settings_menu import advanced_settings_menu
    await query.message.edit_text(
        "<b>⚙️ Advanced Settings</b>",
        reply_markup=await advanced_settings_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^toggle_softsubs$"))
async def toggle_softsubs_callback(client: Client, query: CallbackQuery):
    """Toggle softsubs"""
    from bot.utils.db_handler import get_db
    from bot.keyboards.settings_menu import subtitle_settings_menu
    db = get_db()
    user_id = query.from_user.id
    
    current = await db.get_subtitles(user_id)
    await db.update_setting(user_id, 'subtitles', not current)
    
    await query.message.edit_reply_markup(reply_markup=await subtitle_settings_menu(user_id))
    await query.answer(f"Softsubs {'Enabled' if not current else 'Disabled'}!")

@bot.on_callback_query(filters.regex(r"^toggle_hardsubs$"))
async def toggle_hardsubs_callback(client: Client, query: CallbackQuery):
    """Toggle hardsubs"""
    from bot.utils.db_handler import get_db
    from bot.keyboards.settings_menu import subtitle_settings_menu
    db = get_db()
    user_id = query.from_user.id
    
    current = await db.get_hardsub(user_id)
    await db.update_setting(user_id, 'hardsub', not current)
    
    await query.message.edit_reply_markup(reply_markup=await subtitle_settings_menu(user_id))
    await query.answer(f"Hardsubs {'Enabled' if not current else 'Disabled'}!")

@bot.on_callback_query(filters.regex(r"^toggle_watermark$"))
async def toggle_watermark_callback(client: Client, query: CallbackQuery):
    """Toggle watermark"""
    from bot.utils.db_handler import get_db
    from bot.keyboards.settings_menu import watermark_settings_menu
    db = get_db()
    user_id = query.from_user.id
    
    current = await db.get_watermark(user_id)
    await db.update_setting(user_id, 'watermark_enabled', not current)
    
    await query.message.edit_reply_markup(reply_markup=await watermark_settings_menu(user_id))
    await query.answer(f"Watermark {'Enabled' if not current else 'Disabled'}!")

@bot.on_callback_query(filters.regex(r"^wm_pos_menu$"))
async def wm_pos_menu_callback(client: Client, query: CallbackQuery):
    """Show watermark position menu (Fixed)"""
    from bot.keyboards.menus import watermark_position_menu
    await query.message.edit_text(
        "<b>📍 Select Watermark Position</b>",
        reply_markup=watermark_position_menu(query.from_user.id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^reset_settings_confirm$"))
async def reset_settings_confirm_callback(client: Client, query: CallbackQuery):
    """Reset all settings"""
    from bot.utils.db_handler import get_db
    db = get_db()
    user_id = query.from_user.id
    
    await db.delete_user(user_id)
    await db.add_user(user_id, query.from_user.username, query.from_user.first_name) # Re-add with defaults
    
    from bot.keyboards.settings_menu import open_settings
    await query.message.edit_text(
        "✅ <b>All Settings Reset!</b>",
        reply_markup=await open_settings(user_id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^toggle_default_destination$"))
async def toggle_default_destination_callback(client: Client, query: CallbackQuery):
    """Toggle default upload destination between Telegram and Google Drive."""
    from bot.utils.db_handler import get_db
    from bot.keyboards.settings_menu import advanced_settings_menu

    db = get_db()
    user_id = query.from_user.id

    if not db:
        await query.answer("Database not connected.", show_alert=True)
        return

    current = await db.get_default_destination(user_id)
    new_val = "gdrive" if current == "telegram" else "telegram"
    await db.set_default_destination(user_id, new_val)

    await query.message.edit_reply_markup(
        reply_markup=await advanced_settings_menu(user_id)
    )
    await query.answer(f"Default upload set to {'Google Drive' if new_val == 'gdrive' else 'Telegram'}.")

@bot.on_callback_query(filters.regex(r"^set_audio_codec_menu$"))
async def set_audio_codec_menu_callback(client: Client, query: CallbackQuery):
    """Audio Codec Menu"""
    # Just simple prompt for now or menu
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
        
    user_data[user_id]['waiting_for'] = 'enc_acodec'
    await query.message.edit_text(
        "<b>🔊 Set Audio Codec</b>\nSend codec name (e.g. <code>aac</code>, <code>libmp3lame</code>)",
        reply_markup=close_button(user_id)
    )
    await query.answer()

@bot.on_callback_query(filters.regex(r"^set_channels_menu$"))
async def set_channels_menu_callback(client: Client, query: CallbackQuery):
    """Audio Channels Menu"""
    # Simple prompt
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
        
    user_data[user_id]['waiting_for'] = 'enc_channels'
    await query.message.edit_text(
        "<b>🔊 Set Audio Channels</b>\nSend number (e.g. <code>2.0</code>, <code>5.1</code>)",
        reply_markup=close_button(user_id)
    )
    await query.answer()
