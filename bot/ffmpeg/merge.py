#!/usr/bin/env python3
"""Video merging operations - Vid+Vid, Vid+Aud, Vid+Sub"""

import os
import asyncio
import logging
from typing import Callable, Tuple

from bot.ffmpeg.core import FFmpeg, run_ffmpeg_command

LOGGER = logging.getLogger(__name__)


async def merge_videos(
    video1: str,
    video2: str,
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Merge two videos (concatenate)"""
    
    # Create concat file
    concat_file = output + ".concat.txt"
    with open(concat_file, 'w') as f:
        f.write(f"file '{video1}'\n")
        f.write(f"file '{video2}'\n")
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    
    if success:
        try:
            os.remove(concat_file)
        except:
            pass
        return True, output

    # Fallback: Try Re-encoding (Concat Filter)
    # This handles different codecs/resolutions but is slower
    LOGGER.warning(f"Copy merge failed: {result}. Retrying with re-encode...")
    
    # Note: parsing streams is complex, assuming 1 video 1 audio for now
    # Ideally should probe files to see if audio exists
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', video1,
        '-i', video2,
        '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]',
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '192k',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    
    try:
        os.remove(concat_file)
    except:
        pass
    
    return success, result if not success else output


async def add_audio_to_video(
    video_file: str,
    audio_file: str,
    output: str,
    replace: bool = False,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Add or replace audio track in video"""
    
    if replace:
        # Replace existing audio
        cmd = [
            'ffmpeg', '-y', '-hide_banner',
            '-i', video_file,
            '-i', audio_file,
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            output
        ]
    else:
        # Add as additional track
        cmd = [
            'ffmpeg', '-y', '-hide_banner',
            '-i', video_file,
            '-i', audio_file,
            '-map', '0',
            '-map', '1:a',
            '-c', 'copy',
            output
        ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def add_subtitle_to_video(
    video_file: str,
    subtitle_file: str,
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Add subtitle track to video (soft sub)"""
    
    # Get subtitle extension for proper codec
    sub_ext = os.path.splitext(subtitle_file)[1].lower()
    
    if sub_ext in ['.srt', '.ass', '.ssa']:
        sub_codec = 'copy'
    else:
        sub_codec = 'srt'
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', video_file,
        '-i', subtitle_file,
        '-map', '0',
        '-map', '1',
        '-c', 'copy',
        '-c:s', sub_codec,
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def swap_streams(
    video_file: str,
    output: str,
    video_stream: int = 0,
    audio_stream: int = 0,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Swap/reorder streams in video"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', video_file,
        '-map', f'0:v:{video_stream}',
        '-map', f'0:a:{audio_stream}',
        '-map', '0:s?',
        '-c', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output
