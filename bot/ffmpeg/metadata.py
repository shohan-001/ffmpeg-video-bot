#!/usr/bin/env python3
"""Metadata editing operations"""

import asyncio
import logging
from typing import Tuple, Dict

LOGGER = logging.getLogger(__name__)


async def edit_metadata(
    input_file: str,
    output: str,
    metadata: Dict[str, str]
) -> Tuple[bool, str]:
    """
    Edit video metadata
    
    Args:
        metadata: Dict with keys like 'title', 'author', 'album', 'year', etc.
    """
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file
    ]
    
    # Add metadata flags
    for key, value in metadata.items():
        if value:
            cmd.extend(['-metadata', f'{key}={value}'])
    
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


async def edit_stream_metadata(
    input_file: str,
    output: str,
    stream_type: str,  # 'v', 'a', 's'
    stream_index: int,
    metadata: Dict[str, str]
) -> Tuple[bool, str]:
    """Edit metadata for specific stream"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file
    ]
    
    for key, value in metadata.items():
        if value:
            cmd.extend([f'-metadata:s:{stream_type}:{stream_index}', f'{key}={value}'])
    
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


async def clear_metadata(input_file: str, output: str) -> Tuple[bool, str]:
    """Remove all metadata from video"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-map_metadata', '-1',
        '-c', 'copy',
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


async def set_audio_language(
    input_file: str,
    output: str,
    stream_index: int,
    language: str
) -> Tuple[bool, str]:
    """Set language tag for audio stream"""
    
    return await edit_stream_metadata(
        input_file, output, 'a', stream_index,
        {'language': language}
    )


async def set_subtitle_language(
    input_file: str,
    output: str,
    stream_index: int,
    language: str
) -> Tuple[bool, str]:
    """Set language tag for subtitle stream"""
    
    return await edit_stream_metadata(
        input_file, output, 's', stream_index,
        {'language': language}
    )


async def add_cover_image(
    input_file: str,
    cover_image: str,
    output: str
) -> Tuple[bool, str]:
    """Add cover image to video (for MKV/MP4)"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-i', cover_image,
        '-map', '0',
        '-map', '1',
        '-c', 'copy',
        '-disposition:v:1', 'attached_pic',
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
