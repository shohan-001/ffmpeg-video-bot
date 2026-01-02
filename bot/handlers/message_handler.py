#!/usr/bin/env python3
"""Handler for text messages (input for various operations)"""

import os
from pyrogram import Client, filters
from pyrogram.types import Message

from bot import bot, user_data, LOGGER
from bot.keyboards.menus import main_menu, close_button, confirm_menu, encode_menu, watermark_menu, after_process_menu
from bot.handlers.callbacks import process_video

@bot.on_message(filters.private & filters.text & ~filters.command(["start", "help", "settings", "stats", "ping", "update", "restart", "shell", "log", "broadcast"]))
async def handle_text_input(client: Client, message: Message):
    """Handle text input for various operations"""
    user = message.from_user
    user_id = user.id
    
    # Debug log
    # LOGGER.info(f"Received text from {user_id}: {message.text}")
    
    if user_id not in user_data:
        # If user sends text but has no session, ignore or maybe reply?
        # For now, silently ignore as it might be random chat
        return
        
    waiting_for = user_data[user_id].get('waiting_for')
    
    if not waiting_for:
        return
        
    text = message.text
    LOGGER.info(f"Processing input '{text}' for state '{waiting_for}' from user {user_id}")
    
    # Mock classes for reusing callback logic
    class MockMessage:
        def __init__(self, msg):
            self.chat = msg.chat
            self.id = msg.id
            self._msg = msg
            
        async def edit_text(self, text, reply_markup=None):
            return await self._msg.reply_text(text, reply_markup=reply_markup)
        
        async def delete(self):
            pass 

    class MockQuery:
        def __init__(self, msg, user):
            self.message = MockMessage(msg)
            self.from_user = user
            self.data = f"mock_{user.id}"

    # Handle different inputs
    if waiting_for == 'metadata_input':
        # ... logic ...
        # Parse metadata input
        # Format: key: value
        metadata = {}
        lines = text.split('\n')
        
        # If single line and no colon, assume title
        if len(lines) == 1 and ':' not in lines[0]:
            metadata['title'] = lines[0]
        else:
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip().lower()] = value.strip()
        
        user_data[user_id]['metadata'] = metadata
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(
            f"✅ Metadata received!\n\n"
            f"<b>Title:</b> {metadata.get('title', 'N/A')}\n"
            f"<b>Author:</b> {metadata.get('author', 'N/A')}\n\n"
            "Starting process...",
            quote=True
        )
        await process_video(client, MockQuery(message, user), 'metadata', {'metadata': metadata})

    elif waiting_for == 'ffmpeg_cmd':
        # Validate command
        cmd = text.strip()
        user_data[user_id]['ffmpeg_args'] = cmd
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(f"✅ Executing custom command...", quote=True)
        await process_video(client, MockQuery(message, user), 'ffmpeg_cmd', {'args': cmd})

    elif waiting_for == 'sub_intro_text':
        user_data[user_id]['sub_intro_text'] = text
        user_data[user_id]['waiting_for'] = None
        await message.reply_text("✅ Intro text received! Processing...", quote=True)
        await process_video(client, MockQuery(message, user), 'sub_intro', {'text': text})

    elif waiting_for == 'watermark_text':
        user_data[user_id]['watermark_text'] = text
        user_data[user_id]['waiting_for'] = None
        
        if 'watermark_settings' not in user_data[user_id]:
            user_data[user_id]['watermark_settings'] = {}
        user_data[user_id]['watermark_settings']['text'] = text
        
        await message.reply_text(
            "✅ Watermark text saved!\n\n"
            "Now configure position, opacity, etc.",
            reply_markup=watermark_menu(user_id)
        )

    elif waiting_for == 'trim_input':
        # Parse trim times
        parts = text.split()
        if len(parts) == 1:
            start = parts[0]
            end = None
        elif len(parts) >= 2:
            start = parts[0]
            end = parts[1]
        else:
            await message.reply_text("❌ Invalid format. Try again.")
            return
            
        user_data[user_id]['trim_times'] = (start, end)
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text("✅ Trim times received! Processing...", quote=True)
        await process_video(client, MockQuery(message, user), 'trim', {'start': start, 'end': end})

    elif waiting_for == 'rename':
        new_name = text.strip()
        user_data[user_id]['rename_to'] = new_name
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(f"✅ Renaming to: <b>{new_name}</b>... Processing...", quote=True)
        await process_video(client, MockQuery(message, user), 'rename', {'new_name': new_name})

    elif waiting_for.startswith('enc_'):
        # Encoding settings
        setting = waiting_for.replace('enc_', '')
        
        if 'settings' not in user_data[user_id]:
            user_data[user_id]['settings'] = {}
            
        user_data[user_id]['settings'][setting] = text.strip()
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(
            f"✅ <b>{setting.upper()}</b> set to: <code>{text}</code>",
            reply_markup=encode_menu(user_id)
        )

    elif waiting_for == 'wm_opacity':
        try:
            opacity = float(text)
            if not 0.0 < opacity <= 1.0:
                raise ValueError
        except:
            await message.reply_text("❌ Invalid value. Send a number between 0.1 and 1.0")
            return
            
        if 'watermark_settings' not in user_data[user_id]:
            user_data[user_id]['watermark_settings'] = {}
        user_data[user_id]['watermark_settings']['opacity'] = opacity
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(
            f"✅ Opacity set to: {opacity}",
            reply_markup=watermark_menu(user_id)
        )

    elif waiting_for == 'ss_count':
        try:
            count = int(text)
            if count <= 0:
                raise ValueError
        except:
            await message.reply_text("❌ Invalid number. Please enter a positive integer.")
            return
            
        user_data[user_id]['waiting_for'] = None
        
        await message.reply_text(f"✅ Screenshot count set to {count}. Processing...", quote=True)
        await process_video(client, MockQuery(message, user), 'extract_screenshots', {'count': count})

    elif waiting_for == 'sample_duration':
        # Can accept "30", "30s", "10"
        val = text.lower().replace('s', '').strip()
        try:
            duration = int(val)
            if duration <= 0:
                raise ValueError
        except:
            await message.reply_text("❌ Invalid duration. Please enter a positive number of seconds.")
            return
            
        # Store duration, ask for start type
        user_data[user_id]['sample_duration'] = duration
        user_data[user_id]['waiting_for'] = None
        
        # Show Start Menu
        from bot.keyboards.menus import sample_start_menu
        await message.reply_text(
            f"✅ Duration set to {duration}s.\n\nNow select start time:",
            reply_markup=sample_start_menu(user_id)
        )

    elif waiting_for == 'sample_start':
        # Expect timestamp 00:00:10
        start_time = text.strip()
        user_data[user_id]['sample_start'] = start_time
        user_data[user_id]['waiting_for'] = None
        
        # Determine duration from stored
        duration = user_data[user_id].get('sample_duration', 30)
        
        await message.reply_text(f"⏳ Generating {duration}s sample starting at {start_time}...", quote=True)
        await process_video(client, MockQuery(message, user), 'generate_sample', 
                            {'duration': duration, 'start': start_time})

