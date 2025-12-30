#!/usr/bin/env python3
"""Video effects - Watermark, Subtitle Intro, Hardsub"""

import os
import asyncio
import logging
from typing import Callable, Tuple

from bot.ffmpeg.core import FFmpeg, run_ffmpeg_command

LOGGER = logging.getLogger(__name__)


async def add_image_watermark(
    input_file: str,
    watermark_image: str,
    output: str,
    position: str = 'bottom_right',
    opacity: float = 0.7,
    scale: float = 0.15,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Add image watermark to video"""
    
    # Position mapping (x:y)
    positions = {
        'top_left': '10:10',
        'top_center': '(W-w)/2:10',
        'top_right': 'W-w-10:10',
        'middle_left': '10:(H-h)/2',
        'center': '(W-w)/2:(H-h)/2',
        'middle_right': 'W-w-10:(H-h)/2',
        'bottom_left': '10:H-h-10',
        'bottom_center': '(W-w)/2:H-h-10',
        'bottom_right': 'W-w-10:H-h-10',
    }
    
    pos = positions.get(position, 'W-w-10:H-h-10')
    
    # Scale watermark relative to video
    filter_complex = (
        f"[1:v]scale=iw*{scale}:-1,format=rgba,"
        f"colorchannelmixer=aa={opacity}[wm];"
        f"[0:v][wm]overlay={pos}"
    )
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-i', watermark_image,
        '-filter_complex', filter_complex,
        '-c:a', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def add_text_watermark(
    input_file: str,
    text: str,
    output: str,
    position: str = 'bottom_right',
    font_size: int = 24,
    font_color: str = 'white',
    opacity: float = 0.7,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Add text watermark to video"""
    
    # Position mapping
    positions = {
        'top_left': 'x=10:y=10',
        'top_center': 'x=(w-text_w)/2:y=10',
        'top_right': 'x=w-text_w-10:y=10',
        'middle_left': 'x=10:y=(h-text_h)/2',
        'center': 'x=(w-text_w)/2:y=(h-text_h)/2',
        'middle_right': 'x=w-text_w-10:y=(h-text_h)/2',
        'bottom_left': 'x=10:y=h-text_h-10',
        'bottom_center': 'x=(w-text_w)/2:y=h-text_h-10',
        'bottom_right': 'x=w-text_w-10:y=h-text_h-10',
    }
    
    pos = positions.get(position, 'x=w-text_w-10:y=h-text_h-10')
    
    # Escape special characters in text
    escaped_text = text.replace("'", "\\'").replace(":", "\\:")
    
    drawtext = (
        f"drawtext=text='{escaped_text}':"
        f"{pos}:"
        f"fontsize={font_size}:"
        f"fontcolor={font_color}@{opacity}:"
        f"shadowcolor=black@0.5:shadowx=2:shadowy=2"
    )
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-vf', drawtext,
        '-c:a', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def burn_subtitles(
    input_file: str,
    subtitle_file: str,
    output: str,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Burn subtitles into video (hardsub)"""
    
    ffmpeg = FFmpeg(input_file, output)
    
    # Handle different subtitle formats
    sub_ext = os.path.splitext(subtitle_file)[1].lower()
    
    # Escape file path for filter
    escaped_sub = subtitle_file.replace('\\', '/').replace(':', '\\:')
    
    if sub_ext in ['.ass', '.ssa']:
        subtitle_filter = f"ass='{escaped_sub}'"
    else:
        subtitle_filter = f"subtitles='{escaped_sub}'"
    
    cmd = [
        '-vf', subtitle_filter,
        '-c:v', 'libx264',
        '-crf', '23',
        '-preset', 'medium',
        '-c:a', 'copy'
    ]
    
    success, error = await ffmpeg.run_ffmpeg(cmd, progress_callback, duration)
    
    if not success:
        return False, error
    
    return True, output


async def burn_embedded_subtitles(
    input_file: str,
    output: str,
    subtitle_index: int = 0,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Burn embedded subtitles from video itself"""
    
    ffmpeg = FFmpeg(input_file, output)
    
    cmd = [
        '-filter_complex', f"[0:v][0:s:{subtitle_index}]overlay",
        '-c:v', 'libx264',
        '-crf', '23',
        '-preset', 'medium',
        '-c:a', 'copy'
    ]
    
    success, error = await ffmpeg.run_ffmpeg(cmd, progress_callback, duration)
    
    if not success:
        return False, error
    
    return True, output


async def add_subtitle_intro(
    input_file: str,
    output: str,
    intro_text: str,
    duration: float = 3.0,
    font_size: int = 48,
    font_color: str = 'white',
    progress_callback: Callable = None,
    video_duration: float = None
) -> Tuple[bool, str]:
    """Add text intro at the beginning of video"""
    
    escaped_text = intro_text.replace("'", "\\'").replace(":", "\\:")
    
    # Show intro text for specified duration, then hide
    drawtext = (
        f"drawtext=text='{escaped_text}':"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"fontsize={font_size}:"
        f"fontcolor={font_color}:"
        f"shadowcolor=black@0.5:shadowx=2:shadowy=2:"
        f"enable='lt(t,{duration})'"
    )
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-vf', drawtext,
        '-c:a', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, video_duration)
    return success, result if not success else output


async def add_video_overlay(
    main_video: str,
    overlay_video: str,
    output: str,
    position: str = 'bottom_right',
    scale: float = 0.25,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Add picture-in-picture video overlay"""
    
    positions = {
        'top_left': '10:10',
        'top_right': 'W-w-10:10',
        'bottom_left': '10:H-h-10',
        'bottom_right': 'W-w-10:H-h-10',
    }
    
    pos = positions.get(position, 'W-w-10:H-h-10')
    
    filter_complex = (
        f"[1:v]scale=iw*{scale}:-1[pip];"
        f"[0:v][pip]overlay={pos}"
    )
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', main_video,
        '-i', overlay_video,
        '-filter_complex', filter_complex,
        '-c:a', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output
