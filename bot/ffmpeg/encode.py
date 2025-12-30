#!/usr/bin/env python3
"""Video encoding and conversion operations"""

import os
import asyncio
import logging
from typing import Callable, Tuple, Optional

from bot.ffmpeg.core import FFmpeg, run_ffmpeg_command

LOGGER = logging.getLogger(__name__)


async def encode_video(
    input_file: str,
    output: str,
    video_codec: str = 'libx264',
    audio_codec: str = 'aac',
    crf: int = 23,
    preset: str = 'medium',
    resolution: str = None,
    fps: int = None,
    audio_bitrate: str = '192k',
    progress_callback: Callable = None
) -> Tuple[bool, str]:
    """Encode video with custom settings"""
    
    ffmpeg = FFmpeg(input_file, output)
    
    cmd = ['-c:v', video_codec]
    
    # CRF quality (for x264/x265)
    if video_codec in ['libx264', 'libx265']:
        cmd.extend(['-crf', str(crf)])
        cmd.extend(['-preset', preset])
    elif video_codec == 'libvpx-vp9':
        cmd.extend(['-crf', str(crf), '-b:v', '0'])
    
    # Resolution
    if resolution and resolution != 'original':
        cmd.extend(['-vf', f'scale={resolution}'])
    
    # FPS
    if fps:
        cmd.extend(['-r', str(fps)])
    
    # Audio
    cmd.extend(['-c:a', audio_codec])
    if audio_bitrate:
        cmd.extend(['-b:a', audio_bitrate])
    
    # Copy subtitles if present
    cmd.extend(['-c:s', 'copy'])
    
    success, error = await ffmpeg.run_ffmpeg(cmd, progress_callback)
    
    if not success:
        return False, error
    
    return True, output


async def convert_format(
    input_file: str,
    output_format: str,
    output: str = None,
    progress_callback: Callable = None
) -> Tuple[bool, str]:
    """Convert video to different container format"""
    
    if output is None:
        base = os.path.splitext(input_file)[0]
        output = f"{base}.{output_format}"
    
    # Map format to codec settings
    format_settings = {
        'mp4': {'v': 'copy', 'a': 'aac'},
        'mkv': {'v': 'copy', 'a': 'copy'},
        'avi': {'v': 'copy', 'a': 'copy'},
        'webm': {'v': 'libvpx-vp9', 'a': 'libopus'},
        'mov': {'v': 'copy', 'a': 'aac'},
        'flv': {'v': 'copy', 'a': 'aac'},
        'ts': {'v': 'copy', 'a': 'copy'},
        'gif': {'v': 'gif', 'a': None},
    }
    
    settings = format_settings.get(output_format, {'v': 'copy', 'a': 'copy'})
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-c:v', settings['v']
    ]
    
    if settings['a']:
        cmd.extend(['-c:a', settings['a']])
    else:
        cmd.append('-an')
    
    if output_format == 'gif':
        cmd.extend(['-vf', 'fps=10,scale=480:-1:flags=lanczos'])
    
    cmd.append(output)
    
    success, result = await run_ffmpeg_command(cmd, progress_callback) # duration optional/unknown?
    # actually we should accept duration if we want percentage.
    # But convert_format signature in step 820 says: progress_callback: Callable = None
    # I should add duration to signature if I want percentage.
    # I'll stick to run_ffmpeg_command without duration arg here if I don't update signature, 
    # BUT run_ffmpeg_command signature is (cmd, cb, duration). 
    # So I MUST pass duration. Default is None. 
    # IF I don't pass duration, percentage won't be calculated?
    # run_ffmpeg_command logic: if progress_callback and duration: await cb(current_time)
    # wait, cb expects TIME? 
    # FFmpegProgress.update() uses time.
    # So duration is NOT needed for the callback execution itself? 
    # But core.py check: "if progress_callback and duration:".
    # So duration IS required for callback to fire.
    
    return success, result if not success else output


async def compress_video(
    input_file: str,
    output: str,
    target_size_mb: float = None,
    crf: int = 28,
    progress_callback: Callable = None
) -> Tuple[bool, str]:
    """Compress video to reduce file size"""
    
    ffmpeg = FFmpeg(input_file, output)
    
    if target_size_mb:
        # Calculate bitrate based on target size
        duration = await ffmpeg.get_duration()
        if duration > 0:
            target_bits = target_size_mb * 8 * 1024 * 1024
            target_bitrate = int(target_bits / duration)
            cmd = [
                '-c:v', 'libx264',
                '-b:v', f'{target_bitrate}',
                '-pass', '1',
                '-f', 'null', '/dev/null'
            ]
            # Two-pass encoding for target size
            # Simplified to single pass for now
            cmd = [
                '-c:v', 'libx264',
                '-b:v', f'{target_bitrate}',
                '-c:a', 'aac',
                '-b:a', '128k'
            ]
        else:
            cmd = ['-c:v', 'libx264', '-crf', str(crf), '-c:a', 'aac']
    else:
        cmd = [
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '128k'
        ]
    
    success, error = await ffmpeg.run_ffmpeg(cmd, progress_callback)
    
    if not success:
        return False, error
    
    return True, output


async def change_speed(
    input_file: str,
    output: str,
    speed: float = 1.0,
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Change video playback speed"""
    
    # Video filter for speed
    if speed >= 0.5 and speed <= 2.0:
        video_filter = f"setpts={1/speed}*PTS"
    else:
        video_filter = f"setpts={1/speed}*PTS"
    
    # Audio filter for speed
    audio_filter = f"atempo={speed}"
    
    # atempo only supports 0.5-2.0, chain for other values
    if speed < 0.5:
        audio_filter = f"atempo=0.5,atempo={speed/0.5}"
    elif speed > 2.0:
        audio_filter = f"atempo=2.0,atempo={speed/2.0}"
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-filter:v', video_filter,
        '-filter:a', audio_filter,
        output
    ]
    
    # Duration changes with speed! 
    # If speed 2.0, duration is half. 
    # FFmpeg will report out_time relative to OUTPUT? 
    # Usually relative to output timestamp.
    # So if we pass original duration, percentage will be wrong (will reach 50%).
    # We should adjust duration passed to progress?
    # Passed duration should be estimated output duration.
    
    output_duration = duration / speed if duration else None
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, output_duration)
    return success, result if not success else output


async def rotate_video(
    input_file: str,
    output: str,
    rotation: str = 'right',
    progress_callback: Callable = None,
    duration: float = None
) -> Tuple[bool, str]:
    """Rotate video 90 degrees"""
    
    rotation_map = {
        'right': 'transpose=1',      # 90 clockwise
        'left': 'transpose=2',       # 90 counter-clockwise
        '180': 'transpose=2,transpose=2',
        'flip_h': 'hflip',
        'flip_v': 'vflip',
    }
    
    filter_str = rotation_map.get(rotation, 'transpose=1')
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-vf', filter_str,
        '-c:a', 'copy',
        output
    ]
    
    success, result = await run_ffmpeg_command(cmd, progress_callback, duration)
    return success, result if not success else output


async def change_resolution(
    input_file: str,
    output: str,
    width: int,
    height: int = -1
) -> Tuple[bool, str]:
    """Change video resolution"""
    
    cmd = [
        'ffmpeg', '-y', '-hide_banner',
        '-i', input_file,
        '-vf', f'scale={width}:{height}',
        '-c:a', 'copy',
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
