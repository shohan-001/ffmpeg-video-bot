#!/usr/bin/env python3
"""Stream extraction and removal operations"""

import os
import asyncio
import logging
from typing import Callable, Tuple, List

from bot.ffmpeg.core import run_ffmpeg_command

LOGGER = logging.getLogger(__name__)


async def extract_video(
    input_file: str,
    output: str,
    stream_index: int = 0,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Extract video stream only (no audio)"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-map', f'0:v:{stream_index}',
        '-c', 'copy',
        '-an', '-sn',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def extract_audio(
    input_file: str,
    output: str,
    stream_index: int = 0,
    codec: str = 'mp3',
    bitrate: str = '192k',
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Extract audio stream to specified format"""
    
    codec_map = {
        'mp3': ('libmp3lame', '.mp3'),
        'aac': ('aac', '.m4a'),
        'flac': ('flac', '.flac'),
        'wav': ('pcm_s16le', '.wav'),
        'opus': ('libopus', '.opus'),
        'ogg': ('libvorbis', '.ogg'),
    }
    
    audio_codec, ext = codec_map.get(codec, ('copy', f'.{codec}'))
    
    # Ensure correct extension
    base = os.path.splitext(output)[0]
    output = base + ext
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-map', f'0:a:{stream_index}',
        '-vn',
        '-c:a', audio_codec,
        '-b:a', bitrate,
        output
    ]
    
    if audio_codec == 'copy':
        cmd.remove('-b:a')
        cmd.remove(bitrate)
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def extract_subtitles(
    input_file: str,
    output: str,
    stream_index: int = 0,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Extract subtitle stream"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-map', f'0:s:{stream_index}',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def extract_thumbnail(
    input_file: str,
    output: str,
    timestamp: float = None
) -> Tuple[bool, str]:
    """Extract thumbnail from video"""
    
    if timestamp is None:
        # Get duration and extract from 10%
        cmd_probe = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
        proc = await asyncio.create_subprocess_exec(
            *cmd_probe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        try:
            duration = float(stdout.decode().strip())
            timestamp = duration * 0.1
        except:
            timestamp = 1.0
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-ss', str(timestamp),
        '-i', input_file,
        '-vframes', '1',
        '-q:v', '2',
        output
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        return False, stderr.decode()
    
    return True, output


async def extract_screenshots(
    input_file: str,
    output_dir: str,
    count: int = 10
) -> Tuple[bool, List[str]]:
    """Extract multiple screenshots from video"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get duration
    cmd_probe = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
    proc = await asyncio.create_subprocess_exec(
        *cmd_probe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    
    try:
        duration = float(stdout.decode().strip())
    except:
        return False, []
    
    interval = duration / (count + 1)
    screenshots = []
    
    for i in range(1, count + 1):
        timestamp = interval * i
        output_file = os.path.join(output_dir, f"screenshot_{i:02d}.jpg")
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner',
            '-ss', str(timestamp),
            '-i', input_file,
            '-vframes', '1',
            '-q:v', '2',
            output_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_file):
            screenshots.append(output_file)
    
    return len(screenshots) > 0, screenshots


async def remove_audio(
    input_file: str, 
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Remove all audio streams from video"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-c', 'copy',
        '-an',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def remove_video(
    input_file: str, 
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Remove video stream (keep audio only)"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-c:a', 'copy',
        '-vn',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def remove_subtitles(
    input_file: str, 
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Remove all subtitle streams"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-c', 'copy',
        '-sn',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output
