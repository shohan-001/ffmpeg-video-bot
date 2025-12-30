#!/usr/bin/env python3
"""Core FFmpeg wrapper module"""

import os
import re
import json
import asyncio
import logging
from typing import Optional, Tuple, Dict, Any, Callable

LOGGER = logging.getLogger(__name__)


class FFmpeg:
    """FFmpeg wrapper for video processing"""
    
    def __init__(self, input_file: str, output_file: str = None):
        self.input_file = input_file
        self.output_file = output_file or self._generate_output(input_file)
        self.process = None
        self.cancelled = False
        
    def _generate_output(self, input_file: str) -> str:
        """Generate output filename"""
        base, ext = os.path.splitext(input_file)
        return f"{base}_processed{ext}"
    
    async def get_media_info(self) -> Dict[str, Any]:
        """Get media information using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            self.input_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            LOGGER.error(f"ffprobe error: {stderr.decode()}")
            return {}
        
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError:
            return {}
    
    async def get_duration(self) -> float:
        """Get video duration in seconds"""
        info = await self.get_media_info()
        try:
            return float(info.get('format', {}).get('duration', 0))
        except (ValueError, TypeError):
            return 0
    
    async def get_streams(self) -> Dict[str, list]:
        """Get all streams categorized by type"""
        info = await self.get_media_info()
        streams = info.get('streams', [])
        
        result = {
            'video': [],
            'audio': [],
            'subtitle': [],
            'attachment': []
        }
        
        for stream in streams:
            codec_type = stream.get('codec_type', '')
            if codec_type in result:
                result[codec_type].append(stream)
        
        return result
    
    async def run_ffmpeg(
        self,
        cmd: list,
        progress_callback: Callable = None,
        duration: float = None
    ) -> Tuple[bool, str]:
        """Run FFmpeg command with progress tracking"""
        
        if duration is None:
            duration = await self.get_duration()
        
        # Add progress output option
        full_cmd = ['ffmpeg', '-y', '-hide_banner', '-progress', 'pipe:1', '-i', self.input_file]
        full_cmd.extend(cmd)
        full_cmd.append(self.output_file)
        
        LOGGER.info(f"Running: {' '.join(full_cmd)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Parse progress output
        while True:
            if self.cancelled:
                self.process.terminate()
                return False, "Cancelled"
            
            line = await self.process.stdout.readline()
            if not line:
                break
                
            line = line.decode().strip()
            
            # Parse out_time for progress
            if line.startswith('out_time_ms='):
                try:
                    time_ms = int(line.split('=')[1])
                    current_time = time_ms / 1_000_000
                    if progress_callback and duration > 0:
                        await progress_callback(current_time)
                except ValueError:
                    pass
        
        await self.process.wait()
        
        if self.process.returncode != 0:
            stderr = await self.process.stderr.read()
            error = stderr.decode().strip()
            LOGGER.error(f"FFmpeg error: {error}")
            return False, error
        
        return True, "Success"
    
    def cancel(self):
        """Cancel the running process"""
        self.cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass


async def get_video_info(file_path: str) -> Dict[str, Any]:
    """Get detailed video information"""
    ffmpeg = FFmpeg(file_path)
    info = await ffmpeg.get_media_info()
    
    if not info:
        return {}
    
    result = {
        'filename': os.path.basename(file_path),
        'format': info.get('format', {}).get('format_name', 'Unknown'),
        'duration': float(info.get('format', {}).get('duration', 0)),
        'size': int(info.get('format', {}).get('size', 0)),
        'bitrate': int(info.get('format', {}).get('bit_rate', 0)),
    }
    
    streams = await ffmpeg.get_streams()
    
    # Video info
    if streams['video']:
        video = streams['video'][0]
        result['video'] = {
            'codec': video.get('codec_name', 'Unknown'),
            'width': video.get('width', 0),
            'height': video.get('height', 0),
            'fps': eval(video.get('r_frame_rate', '0/1')),
            'bitrate': int(video.get('bit_rate', 0)),
        }
    
    # Audio info
    if streams['audio']:
        result['audio'] = []
        for audio in streams['audio']:
            result['audio'].append({
                'codec': audio.get('codec_name', 'Unknown'),
                'channels': audio.get('channels', 0),
                'sample_rate': audio.get('sample_rate', '0'),
                'language': audio.get('tags', {}).get('language', 'und'),
            })
    
    # Subtitle info
    if streams['subtitle']:
        result['subtitles'] = []
        for sub in streams['subtitle']:
            result['subtitles'].append({
                'codec': sub.get('codec_name', 'Unknown'),
                'language': sub.get('tags', {}).get('language', 'und'),
            })
    
    return result


async def format_media_info(info: Dict[str, Any]) -> str:
    """Format media info as readable text"""
    if not info:
        return "❌ Could not get media information"
    
    duration_str = f"{int(info['duration'] // 60)}:{int(info['duration'] % 60):02d}"
    size_mb = info['size'] / (1024 * 1024)
    bitrate_kbps = info['bitrate'] / 1000
    
    text = (
        f"<b>📁 File:</b> <code>{info['filename']}</code>\n"
        f"<b>📦 Format:</b> {info['format']}\n"
        f"<b>⏱️ Duration:</b> {duration_str}\n"
        f"<b>💾 Size:</b> {size_mb:.2f} MB\n"
        f"<b>📊 Bitrate:</b> {bitrate_kbps:.0f} kbps\n"
    )
    
    if 'video' in info:
        v = info['video']
        text += (
            f"\n<b>🎬 Video:</b>\n"
            f"  • Codec: {v['codec']}\n"
            f"  • Resolution: {v['width']}x{v['height']}\n"
            f"  • FPS: {v['fps']:.2f}\n"
        )
    
    if 'audio' in info:
        text += f"\n<b>🔊 Audio Tracks:</b> {len(info['audio'])}\n"
        for i, a in enumerate(info['audio'], 1):
            text += f"  {i}. {a['codec']} | {a['channels']}ch | {a['language']}\n"
    
    if 'subtitles' in info:
        text += f"\n<b>📝 Subtitles:</b> {len(info['subtitles'])}\n"
        for i, s in enumerate(info['subtitles'], 1):
            text += f"  {i}. {s['codec']} | {s['language']}\n"
    
    return text
