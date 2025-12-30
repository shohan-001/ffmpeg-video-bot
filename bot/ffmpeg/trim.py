#!/usr/bin/env python3
"""Video trimming operations"""

import asyncio
import logging
from typing import Callable, Tuple

from bot.ffmpeg.core import FFmpeg

LOGGER = logging.getLogger(__name__)


async def trim_video(
    input_file: str,
    output: str,
    start_time: str = None,
    end_time: str = None,
    duration: str = None,
    progress_callback: Callable = None
) -> Tuple[bool, str]:
    """
    Trim video by start/end time or duration
    
    Args:
        start_time: Start time (format: HH:MM:SS or seconds)
        end_time: End time (format: HH:MM:SS or seconds)
        duration: Duration to keep (format: HH:MM:SS or seconds)
    """
    
    cmd = ['ffmpeg', '-y', '-hide_banner']
    
    # Input seeking (fast)
    if start_time:
        cmd.extend(['-ss', str(start_time)])
    
    cmd.extend(['-i', input_file])
    
    # End time or duration
    if end_time:
        cmd.extend(['-to', str(end_time)])
    elif duration:
        cmd.extend(['-t', str(duration)])
    
    # Copy without re-encoding for speed
    cmd.extend(['-c', 'copy', output])
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        return False, stderr.decode()
    
    return True, output


async def trim_video_accurate(
    input_file: str,
    output: str,
    start_time: str,
    end_time: str = None,
    duration: str = None,
    progress_callback: Callable = None
) -> Tuple[bool, str]:
    """
    Trim video with frame-accurate cutting (slower, re-encodes)
    """
    
    ffmpeg = FFmpeg(input_file, output)
    
    cmd = []
    
    if start_time:
        cmd.extend(['-ss', str(start_time)])
    
    if end_time:
        cmd.extend(['-to', str(end_time)])
    elif duration:
        cmd.extend(['-t', str(duration)])
    
    cmd.extend([
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'fast',
        '-c:a', 'aac'
    ])
    
    success, error = await ffmpeg.run_ffmpeg(cmd, progress_callback)
    
    if not success:
        return False, error
    
    return True, output


async def split_video(
    input_file: str,
    output_pattern: str,
    segment_duration: int = 60
) -> Tuple[bool, list]:
    """Split video into segments of specified duration"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-c', 'copy',
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-reset_timestamps', '1',
        output_pattern
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        return False, stderr.decode()
    
    # Find created segments
    import os
    import glob
    
    base_dir = os.path.dirname(output_pattern)
    pattern = output_pattern.replace('%03d', '*')
    segments = sorted(glob.glob(pattern))
    
    return True, segments


def parse_time(time_str: str) -> float:
    """Parse time string to seconds"""
    time_str = str(time_str).strip()
    
    # Already in seconds
    try:
        return float(time_str)
    except ValueError:
        pass
    
    # HH:MM:SS format
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    
    return 0


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
    else:
        return f"{minutes:02d}:{secs:05.2f}"
