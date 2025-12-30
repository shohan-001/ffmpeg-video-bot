#!/usr/bin/env python3
"""Progress tracking for file upload/download and FFmpeg operations"""

import asyncio
import logging
from time import time
from typing import Callable

LOGGER = logging.getLogger(__name__)


class Progress:
    """Progress tracker for uploads/downloads"""
    
    def __init__(
        self,
        message,
        operation: str = "Processing",
        update_interval: float = 3.0,
        user_id: int = None,
        filename: str = None
    ):
        self.message = message
        self.operation = operation
        self.update_interval = update_interval
        self.last_update_time = 0
        self.start_time = time()
        self.user_id = user_id
        self.filename = filename
        self.cancelled = False
    
    def cancel(self):
        """Mark as cancelled"""
        self.cancelled = True
    
    async def progress_callback(self, current: int, total: int):
        """Callback for pyrogram progress"""
        if self.cancelled:
            raise asyncio.CancelledError("Cancelled by user")
        
        now = time()
        
        if now - self.last_update_time < self.update_interval:
            return
            
        self.last_update_time = now
        
        elapsed_time = now - self.start_time
        percentage = (current / total) * 100
        speed = current / elapsed_time if elapsed_time > 0 else 0
        
        if speed > 0:
            eta = (total - current) / speed
        else:
            eta = 0
        
        progress_bar = self._create_progress_bar(percentage)
        
        # Clean operation name (remove emojis if any passed)
        op_name = self.operation.replace("📥 ", "").replace("📤 ", "").replace("️", "").strip()
        
        header = f"<b>{self.filename}</b>\n" if self.filename else ""
        
        text = (
            f"{header}"
            f"┃ {progress_bar} {percentage:.1f}%\n"
            f"├ <b>Processed:</b> {self._format_size(current)} of {self._format_size(total)}\n"
            f"├ <b>Status:</b> {op_name} | <b>ETA:</b> {self._format_time(eta)}\n"
            f"├ <b>Speed:</b> {self._format_size(speed)}/s | <b>Elapsed:</b> {self._format_time(elapsed_time)}\n"
            f"├ <b>User ID:</b> {self.user_id or 'Unknown'}"
        )
        
        # Add cancel button (No Emoji)
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        cancel_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("Cancel", callback_data=f"cancel_process_{self.user_id or 0}")
        ]]) if self.user_id else None
        
        try:
            await self.message.edit_text(text, reply_markup=cancel_btn)
        except Exception as e:
            LOGGER.debug(f"Progress update error: {e}")
    
    @staticmethod
    def _create_progress_bar(percentage: float, length: int = 12) -> str:
        """Create a visual progress bar"""
        custom_fill = "■"
        custom_empty = "□"
        
        filled = int(length * percentage / 100)
        empty = length - filled
        return f"[{custom_fill * filled}{custom_empty * empty}]"
    
    @staticmethod
    def _format_size(size_bytes: float) -> str:
        """Format bytes to human readable"""
        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024
            unit_index += 1
        
        return f"{size_bytes:.2f}{units[unit_index]}"
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to readable time"""
        if seconds < 0: return "0s"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


class FFmpegProgress:
    """Progress tracker for FFmpeg operations"""
    
    def __init__(
        self,
        message,
        duration: float,
        operation: str = "Processing",
        update_interval: float = 3.0,
        filename: str = None
    ):
        self.message = message
        self.duration = duration
        self.operation = operation
        self.update_interval = update_interval
        self.last_update_time = 0
        self.start_time = time()
        self.filename = filename
    
    async def update(self, current_time: float):
        """Update progress based on current timestamp"""
        now = time()
        
        if now - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = now
        
        if self.duration > 0:
            percentage = min((current_time / self.duration) * 100, 100)
        else:
            percentage = 0
        
        elapsed = now - self.start_time
        
        if percentage > 0:
            eta = (elapsed / percentage) * (100 - percentage)
        else:
            eta = 0
        
        progress_bar = Progress._create_progress_bar(percentage)
        
        op_name = self.operation.replace("⚙️ ", "").replace("️", "").strip()
        header = f"<b>{self.filename}</b>\n" if self.filename else ""
        
        text = (
            f"{header}"
            f"┃ {progress_bar} {percentage:.1f}%\n"
            f"├ <b>Status:</b> {op_name}\n"
            f"├ <b>Time:</b> {self._format_time(current_time)} / {self._format_time(self.duration)}\n"
            f"├ <b>Elapsed:</b> {self._format_time(elapsed)}\n"
            f"├ <b>ETA:</b> {self._format_time(eta)}"
        )
        
        try:
            await self.message.edit_text(text)
        except Exception as e:
            LOGGER.debug(f"FFmpeg progress update error: {e}")
    
    # Helper method re-used from Progress
    _format_time = Progress._format_time
