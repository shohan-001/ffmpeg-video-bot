#!/usr/bin/env python3
"""Utility functions"""

import os
import asyncio
import logging
from time import time
from typing import Callable, Any

LOGGER = logging.getLogger(__name__)

def get_readable_file_size(size_in_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_in_bytes is None:
        return "0B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_in_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def get_readable_time(seconds: int) -> str:
    """Convert seconds to human readable format"""
    if seconds < 0:
        return "0s"
        
    periods = [
        ('d', 86400),
        ('h', 3600),
        ('m', 60),
        ('s', 1)
    ]
    
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{int(period_value)}{period_name}")
    
    return ' '.join(result) if result else "0s"


async def run_cmd(cmd: list | str) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and return code"""
    if isinstance(cmd, str):
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    else:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    stdout, stderr = await process.communicate()
    return stdout.decode().strip(), stderr.decode().strip(), process.returncode


def get_video_extensions() -> list:
    """Get list of supported video extensions"""
    return [
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
        '.webm', '.m4v', '.3gp', '.ts', '.mts', '.m2ts',
        '.vob', '.ogv', '.mpg', '.mpeg', '.divx'
    ]


def get_audio_extensions() -> list:
    """Get list of supported audio extensions"""
    return [
        '.mp3', '.aac', '.flac', '.wav', '.ogg', '.wma',
        '.m4a', '.opus', '.ac3', '.dts', '.eac3'
    ]


def get_subtitle_extensions() -> list:
    """Get list of supported subtitle extensions"""
    return ['.srt', '.ass', '.ssa', '.vtt', '.sub', '.idx']


def is_video_file(filename: str) -> bool:
    """Check if file is a video"""
    return os.path.splitext(filename.lower())[1] in get_video_extensions()


def is_audio_file(filename: str) -> bool:
    """Check if file is an audio file"""
    return os.path.splitext(filename.lower())[1] in get_audio_extensions()


def is_subtitle_file(filename: str) -> bool:
    """Check if file is a subtitle"""
    return os.path.splitext(filename.lower())[1] in get_subtitle_extensions()


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


async def clean_temp_files(directory: str, max_age_hours: int = 24):
    """Clean temporary files older than max_age_hours"""
    current_time = time()
    max_age_seconds = max_age_hours * 3600
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    LOGGER.info(f"Cleaned old file: {file_path}")
            except Exception as e:
                LOGGER.error(f"Error cleaning file {file_path}: {e}")
