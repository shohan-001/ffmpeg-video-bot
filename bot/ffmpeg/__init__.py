# FFmpeg module
from bot.ffmpeg.core import FFmpeg, get_video_info, format_media_info
from bot.ffmpeg.encode import encode_video, convert_format, compress_video, change_speed, rotate_video
from bot.ffmpeg.extract import (
    extract_video, extract_audio, extract_subtitles, 
    extract_thumbnail, extract_screenshots,
    remove_audio, remove_video, remove_subtitles
)
from bot.ffmpeg.merge import merge_videos, add_audio_to_video, add_subtitle_to_video, swap_streams
from bot.ffmpeg.effects import (
    add_image_watermark, add_text_watermark, 
    burn_subtitles, burn_embedded_subtitles,
    add_subtitle_intro, add_video_overlay
)
from bot.ffmpeg.trim import trim_video, trim_video_accurate, split_video
from bot.ffmpeg.metadata import edit_metadata, clear_metadata, add_cover_image
