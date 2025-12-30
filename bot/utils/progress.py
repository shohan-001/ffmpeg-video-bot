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
        update_interval: float = 3.0
    ):
        self.message = message
        self.operation = operation
        self.update_interval = update_interval
        self.last_update_time = 0
        self.start_time = time()
    
    async def progress_callback(self, current: int, total: int):
        """Callback for pyrogram progress"""
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
        
        text = (
            f"<b>{self.operation}</b>\n\n"
            f"{progress_bar}\n"
            f"<b>Progress:</b> {percentage:.1f}%\n"
            f"<b>Completed:</b> {self._format_size(current)} / {self._format_size(total)}\n"
            f"<b>Speed:</b> {self._format_size(speed)}/s\n"
            f"<b>ETA:</b> {self._format_time(eta)}"
        )
        
        try:
            await self.message.edit_text(text)
        except Exception as e:
            LOGGER.debug(f"Progress update error: {e}")
    
    @staticmethod
    def _create_progress_bar(percentage: float, length: int = 12) -> str:
        """Create a visual progress bar"""
        filled = int(length * percentage / 100)
        empty = length - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    @staticmethod
    def _format_size(size_bytes: float) -> str:
        """Format bytes to human readable"""
        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024
            unit_index += 1
        
        return f"{size_bytes:.2f} {units[unit_index]}"
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to readable time"""
        if seconds < 0:
            return "0s"
        
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


class FFmpegProgress:
    """Progress tracker for FFmpeg operations"""
    
    def __init__(
        self,
        message,
        duration: float,
        operation: str = "Processing",
        update_interval: float = 3.0
    ):
        self.message = message
        self.duration = duration
        self.operation = operation
        self.update_interval = update_interval
        self.last_update_time = 0
        self.start_time = time()
    
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
        
        text = (
            f"<b>🎬 {self.operation}</b>\n\n"
            f"{progress_bar}\n"
            f"<b>Progress:</b> {percentage:.1f}%\n"
            f"<b>Time:</b> {Progress._format_time(current_time)} / {Progress._format_time(self.duration)}\n"
            f"<b>Elapsed:</b> {Progress._format_time(elapsed)}\n"
            f"<b>ETA:</b> {Progress._format_time(eta)}"
        )
        
        try:
            await self.message.edit_text(text)
        except Exception as e:
            LOGGER.debug(f"FFmpeg progress update error: {e}")
