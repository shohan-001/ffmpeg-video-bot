#!/usr/bin/env python3
"""Handler for text messages (input for various operations)"""

import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

from bot import bot, user_data, LOGGER, AUTHORIZED_GROUPS
from bot.keyboards.menus import main_menu, close_button, confirm_menu, encode_menu, watermark_menu, after_process_menu
from bot.handlers.callbacks import process_video


# Mock classes for reusing callback logic (must be at module level for import)
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
    
    async def answer(self, text=None, show_alert=False):
        pass  # Callback queries have answer method

@bot.on_message(filters.text & ~filters.command(["start", "help", "settings", "stats", "ping", "update", "restart", "shell", "log", "broadcast"]))
async def handle_text_input(client: Client, message: Message):
    """Handle text input for various operations"""
    try:
        user = message.from_user
        if not user:
            return
        user_id = user.id

        if user_id not in user_data:
            # If user sends text but has no session
            # Only reply in private to avoid spamming groups
            if message.chat.type == ChatType.PRIVATE:
                # No active session; we keep silent or could show a short hint
                pass
            return
            
        waiting_for = user_data[user_id].get('waiting_for')
        
        # If NOT waiting for input, enforce group authorization
        if not waiting_for:
            if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                if AUTHORIZED_GROUPS and message.chat.id not in AUTHORIZED_GROUPS:
                    return
            
            # Only reply in private if random text
            if message.chat.type == ChatType.PRIVATE:
                 pass
            return
            
        # We ARE waiting for input, so process it regardless of group
        text = message.text
        LOGGER.info(f"Processing input '{text}' for state '{waiting_for}' from user {user_id}")
        
        # Handle merge_videos URL input
        if waiting_for == 'merge_videos':
            # Check if it's a URL
            if text.startswith('http://') or text.startswith('https://'):
                # Add URL to merge queue
                if 'merge_queue' not in user_data[user_id]:
                    user_data[user_id]['merge_queue'] = []
                
                user_data[user_id]['merge_queue'].append({
                    'type': 'url',
                    'url': text,
                    'name': text[:50]
                })
                
                count = len(user_data[user_id]['merge_queue'])
                
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Done - Start Merge", callback_data=f"merge_done_{user_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{user_id}")]
                ])
                
                await message.reply_text(
                    f"✅ URL #{count} added!\n\n"
                    f"<b>Queue:</b> {count} videos\n"
                    f"Send more or click <b>Done</b>.",
                    reply_markup=keyboard,
                    quote=True
                )
                return
        
        # Handle different inputs
        if waiting_for == 'metadata_input':
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
            # Encoding settings (persist both in-memory and to DB)
            setting = waiting_for.replace('enc_', '')
            value = text.strip()

            if 'settings' not in user_data[user_id]:
                user_data[user_id]['settings'] = {}
            user_data[user_id]['settings'][setting] = value
            user_data[user_id]['waiting_for'] = None

            # Persist to MongoDB if available
            try:
                from bot.utils.db_handler import get_db
                db = get_db()
                if db:
                    await db.update_setting(user_id, setting, value)
            except Exception:
                pass

            await message.reply_text(
                f"✅ <b>{setting.upper()}</b> set to: <code>{value}</code>",
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

        elif waiting_for == 'new_filename':
            # Handle Rename Input
            from bot.utils.helpers import sanitize_filename
            old_path = user_data[user_id].get('processing_file') or user_data[user_id].get('file_path')
            if not old_path or not os.path.exists(old_path):
                await message.reply_text("❌ Original file lost. Please upload again.")
                return
            
            new_name = sanitize_filename(text.strip())
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            try:
                os.rename(old_path, new_path)
                user_data[user_id]['file_path'] = new_path
                user_data[user_id]['processing_file'] = new_path
                user_data[user_id]['file_name'] = new_name
                user_data[user_id]['waiting_for'] = None
                
                await message.reply_text(
                    f"✅ Renamed to: <code>{new_name}</code>",
                    reply_markup=main_menu(user_id),
                    quote=True
                )
            except Exception as e:
                await message.reply_text(f"❌ Rename failed: {e}")

        elif waiting_for == 'final_rename_input':
            # Handle Final Rename Input
            from bot.utils.helpers import sanitize_filename
            old_path = user_data[user_id].get('output_path')
            if not old_path or not os.path.exists(old_path):
                await message.reply_text("❌ Processed file lost.")
                return
            
            new_name = sanitize_filename(text.strip())
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            try:
                os.rename(old_path, new_path)
                user_data[user_id]['output_path'] = new_path
                user_data[user_id]['waiting_for'] = None
                
                status_msg = await message.reply_text(f"✅ Renamed to: <code>{new_name}</code>\nUploading...")
                
                from bot.handlers.callbacks import upload_processed_file
                await upload_processed_file(client, user_id, status_msg, "telegram")
            except Exception as e:
                await message.reply_text(f"❌ Rename failed: {e}")

        else:
            # Unknown waiting_for state - check if URL
            if text.startswith('http://') or text.startswith('https://'):
                from bot.handlers.file_handler import handle_url_logic
                await handle_url_logic(client, message, text)
            else:
                # Unknown state, just clear it
                LOGGER.warning(f"Unknown waiting_for state: {waiting_for}")
                user_data[user_id]['waiting_for'] = None
                await message.reply_text(f"✅ Input received: <code>{text}</code>", quote=True)

    except Exception as e:
        LOGGER.error(f"Error in text handler: {e}", exc_info=True)
        # Try to notify user if possible, but safely
        try:
             if message.chat.type == ChatType.PRIVATE:
                 await message.reply_text(f"❌ <b>Error:</b> {e}")
        except:
             pass
