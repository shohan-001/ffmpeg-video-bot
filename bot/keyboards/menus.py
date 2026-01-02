#!/usr/bin/env python3
"""Inline keyboard menus for the bot"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Main operation menu after user sends a video"""
    buttons = [
        [
            InlineKeyboardButton("FFMPEG CMD", callback_data=f"ffcmd_{user_id}"),
            InlineKeyboardButton("MegaMetaData", callback_data=f"metadata_{user_id}"),
        ],
        [
            InlineKeyboardButton("Vid+Vid", callback_data=f"vidvid_{user_id}"),
            InlineKeyboardButton("Vid+Aud", callback_data=f"vidaud_{user_id}"),
            InlineKeyboardButton("Vid+Sub", callback_data=f"vidsub_{user_id}"),
        ],
        [
            InlineKeyboardButton("StreamSwap", callback_data=f"streamswap_{user_id}"),
            InlineKeyboardButton("Extract", callback_data=f"extract_{user_id}"),
            InlineKeyboardButton("Remove", callback_data=f"remove_{user_id}"),
        ],
        [
            InlineKeyboardButton("Encode", callback_data=f"encode_{user_id}"),
            InlineKeyboardButton("Convert", callback_data=f"convert_{user_id}"),
            InlineKeyboardButton("Watermark", callback_data=f"watermark_{user_id}"),
        ],
        [
            InlineKeyboardButton("Sub Intro", callback_data=f"subintro_{user_id}"),
            InlineKeyboardButton("Hardsub", callback_data=f"hardsub_{user_id}"),
        ],
        [
            InlineKeyboardButton("Trim", callback_data=f"trim_{user_id}"),
        ],
        [
            InlineKeyboardButton("Speed", callback_data=f"speed_{user_id}"),
            InlineKeyboardButton("Rotate", callback_data=f"rotate_{user_id}"),
        ],
        [
            InlineKeyboardButton("Keep Source", callback_data=f"keepsrc_{user_id}"),
            InlineKeyboardButton("Rename", callback_data=f"rename_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"back_{user_id}"),
            InlineKeyboardButton("Close", callback_data=f"close_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def encode_menu(user_id: int) -> InlineKeyboardMarkup:
    """Encoding options menu"""
    buttons = [
        [
            InlineKeyboardButton("Preset", callback_data=f"enc_preset_{user_id}"),
            InlineKeyboardButton("CRF", callback_data=f"enc_crf_{user_id}"),
        ],
        [
            InlineKeyboardButton("Video Codec", callback_data=f"enc_vcodec_{user_id}"),
            InlineKeyboardButton("Audio Codec", callback_data=f"enc_acodec_{user_id}"),
        ],
        [
            InlineKeyboardButton("Resolution", callback_data=f"enc_res_{user_id}"),
            InlineKeyboardButton("FPS", callback_data=f"enc_fps_{user_id}"),
        ],
        [
            InlineKeyboardButton("Start Encoding", callback_data=f"enc_start_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
            InlineKeyboardButton("Close", callback_data=f"close_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def preset_menu(user_id: int) -> InlineKeyboardMarkup:
    """FFmpeg preset selection"""
    presets = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
    buttons = []
    row = []
    for preset in presets:
        row.append(InlineKeyboardButton(preset, callback_data=f"preset_{preset}_{user_id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"encode_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def resolution_menu(user_id: int) -> InlineKeyboardMarkup:
    """Resolution selection"""
    resolutions = [
        ('480p', '854x480'),
        ('720p', '1280x720'),
        ('1080p', '1920x1080'),
        ('1440p', '2560x1440'),
        ('4K', '3840x2160'),
        ('Original', 'original'),
    ]
    buttons = []
    row = []
    for name, res in resolutions:
        row.append(InlineKeyboardButton(name, callback_data=f"res_{res}_{user_id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"encode_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def convert_menu(user_id: int) -> InlineKeyboardMarkup:
    """Format conversion menu"""
    formats = ['mp4', 'mkv', 'avi', 'webm', 'mov', 'flv', 'ts', 'gif']
    buttons = []
    row = []
    for fmt in formats:
        row.append(InlineKeyboardButton(f".{fmt}", callback_data=f"format_{fmt}_{user_id}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"main_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def extract_menu(user_id: int) -> InlineKeyboardMarkup:
    """Stream extraction menu"""
    buttons = [
        [
            InlineKeyboardButton("Video Only", callback_data=f"ext_video_{user_id}"),
            InlineKeyboardButton("Audio Only", callback_data=f"ext_audio_{user_id}"),
        ],
        [
            InlineKeyboardButton("Subtitles", callback_data=f"ext_subs_{user_id}"),
            InlineKeyboardButton("Thumbnail", callback_data=f"ext_thumb_{user_id}"),
        ],
        [
            InlineKeyboardButton("Screenshots", callback_data=f"ext_ss_{user_id}"),
            InlineKeyboardButton("Sample Video", callback_data=f"ext_sample_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def screenshot_count_menu(user_id: int) -> InlineKeyboardMarkup:
    """Menu to select number of screenshots"""
    buttons = [
        [
            InlineKeyboardButton("3", callback_data=f"sscnt_3_{user_id}"),
            InlineKeyboardButton("5", callback_data=f"sscnt_5_{user_id}"),
            InlineKeyboardButton("7", callback_data=f"sscnt_7_{user_id}"),
            InlineKeyboardButton("10", callback_data=f"sscnt_10_{user_id}"),
        ],
        [
            InlineKeyboardButton("Custom Amount", callback_data=f"sscnt_custom_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"extract_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def sample_duration_menu(user_id: int) -> InlineKeyboardMarkup:
    """Menu to select sample video duration"""
    buttons = [
        [
            InlineKeyboardButton("10s", callback_data=f"sample_10_{user_id}"),
            InlineKeyboardButton("30s", callback_data=f"sample_30_{user_id}"),
            InlineKeyboardButton("60s", callback_data=f"sample_60_{user_id}"),
        ],
        [
            InlineKeyboardButton("Custom Duration", callback_data=f"sample_custom_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"extract_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def sample_start_menu(user_id: int) -> InlineKeyboardMarkup:
    """Menu to select sample start time"""
    buttons = [
        [
            InlineKeyboardButton("Random Start", callback_data=f"samplestart_random_{user_id}"),
        ],
        [
            InlineKeyboardButton("Custom Start", callback_data=f"samplestart_custom_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"extract_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def stream_selection_menu(user_id: int, streams: list, stream_type: str) -> InlineKeyboardMarkup:
    """Menu to select a specific stream"""
    buttons = []
    
    # Callback prefix based on type
    prefix = "selsub" if stream_type == 'subtitle' else "selaud"
    
    for i, stream in enumerate(streams):
        # Format label
        lang = stream.get('tags', {}).get('language', 'und')
        codec = stream.get('codec_name', 'unk')
        title = stream.get('tags', {}).get('title', '')
        
        label = f"{i+1}. {lang} ({codec})"
        if title:
            # Clean title
            title = title[:20].strip()
            label += f" - {title}"
            
        buttons.append([InlineKeyboardButton(label, callback_data=f"{prefix}_{i}_{user_id}")])
        
    buttons.append([InlineKeyboardButton("Back", callback_data=f"extract_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def remove_menu(user_id: int) -> InlineKeyboardMarkup:
    """Stream removal menu"""
    buttons = [
        [
            InlineKeyboardButton("Remove Audio", callback_data=f"rem_audio_{user_id}"),
            InlineKeyboardButton("Remove Video", callback_data=f"rem_video_{user_id}"),
        ],
        [
            InlineKeyboardButton("Remove Subs", callback_data=f"rem_subs_{user_id}"),
            InlineKeyboardButton("Remove Thumb", callback_data=f"rem_thumb_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def watermark_menu(user_id: int) -> InlineKeyboardMarkup:
    """Watermark options"""
    buttons = [
        [
            InlineKeyboardButton("Image Watermark", callback_data=f"wm_image_{user_id}"),
            InlineKeyboardButton("Text Watermark", callback_data=f"wm_text_{user_id}"),
        ],
        [
            InlineKeyboardButton("Position", callback_data=f"wm_pos_{user_id}"),
            InlineKeyboardButton("Opacity", callback_data=f"wm_opacity_{user_id}"),
        ],
        [
            InlineKeyboardButton("Apply", callback_data=f"wm_apply_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def watermark_position_menu(user_id: int) -> InlineKeyboardMarkup:
    """Watermark position selection"""
    positions = [
        ('Top Left', 'top_left'),
        ('Top Center', 'top_center'),
        ('Top Right', 'top_right'),
        ('Middle Left', 'middle_left'),
        ('Center', 'center'),
        ('Middle Right', 'middle_right'),
        ('Bottom Left', 'bottom_left'),
        ('Bottom Center', 'bottom_center'),
        ('Bottom Right', 'bottom_right'),
    ]
    buttons = []
    row = []
    for name, pos in positions:
        row.append(InlineKeyboardButton(name, callback_data=f"wmpos_{pos}_{user_id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"watermark_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def audio_format_menu(user_id: int) -> InlineKeyboardMarkup:
    """Audio extraction format menu"""
    formats = ['mp3', 'aac', 'flac', 'wav', 'opus', 'ogg', 'm4a']
    buttons = []
    row = []
    for fmt in formats:
        row.append(InlineKeyboardButton(f".{fmt}", callback_data=f"audiofmt_{fmt}_{user_id}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"extract_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def confirm_menu(user_id: int, action: str) -> InlineKeyboardMarkup:
    """Confirmation menu"""
    buttons = [
        [
            InlineKeyboardButton("Confirm", callback_data=f"confirm_{action}_{user_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"cancel_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)



def close_button(user_id: int) -> InlineKeyboardMarkup:
    """Simple close button"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Close", callback_data=f"close_{user_id}")
    ]])


def back_and_close_button(user_id: int, back_data: str) -> InlineKeyboardMarkup:
    """Back and Close buttons"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back", callback_data=back_data),
        InlineKeyboardButton("❌ Close", callback_data=f"close_{user_id}")
    ]])


# Additional FFmpeg features menus
def speed_menu(user_id: int) -> InlineKeyboardMarkup:
    """Video speed options"""
    speeds = [
        ('0.25x', '0.25'), ('0.5x', '0.5'), ('0.75x', '0.75'),
        ('1.5x', '1.5'), ('2x', '2'), ('3x', '3'), ('4x', '4'),
    ]
    buttons = []
    row = []
    for name, speed in speeds:
        row.append(InlineKeyboardButton(name, callback_data=f"speed_{speed}_{user_id}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Back", callback_data=f"main_{user_id}")])
    return InlineKeyboardMarkup(buttons)


def rotate_menu(user_id: int) -> InlineKeyboardMarkup:
    """Video rotation options"""
    buttons = [
        [
            InlineKeyboardButton("90° Left", callback_data=f"rotate_left_{user_id}"),
            InlineKeyboardButton("90° Right", callback_data=f"rotate_right_{user_id}"),
        ],
        [
            InlineKeyboardButton("180°", callback_data=f"rotate_180_{user_id}"),
            InlineKeyboardButton("Flip H", callback_data=f"flip_h_{user_id}"),
            InlineKeyboardButton("Flip V", callback_data=f"flip_v_{user_id}"),
        ],
        [
            InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def upload_destination_menu(user_id: int, gdrive_enabled: bool = True) -> InlineKeyboardMarkup:
    """Upload destination selection menu"""
    buttons = [
        [
            InlineKeyboardButton("Telegram", callback_data=f"upload_tg_{user_id}"),
        ],
    ]
    
    if gdrive_enabled:
        buttons.append([
            InlineKeyboardButton("Google Drive", callback_data=f"upload_gdrive_{user_id}"),
        ])
    
    buttons.append([
        InlineKeyboardButton("Back", callback_data=f"main_{user_id}"),
        InlineKeyboardButton("Close", callback_data=f"close_{user_id}"),
    ])
    
    return InlineKeyboardMarkup(buttons)


def after_process_menu(user_id: int, file_size_mb: float, gdrive_enabled: bool = True) -> InlineKeyboardMarkup:
    """Menu shown after processing, with upload options based on file size"""
    buttons = []
    
    # If file is under 2GB, Telegram upload is available
    if file_size_mb < 2000:
        buttons.append([
            InlineKeyboardButton("Upload to Telegram", callback_data=f"finalup_tg_{user_id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton("Too large for Telegram (>2GB)", callback_data=f"none_{user_id}"),
        ])
    
    # Google Drive is always available if enabled
    if gdrive_enabled:
        buttons.append([
            InlineKeyboardButton("Upload to Google Drive", callback_data=f"finalup_gdrive_{user_id}"),
        ])
    
    buttons.append([
        InlineKeyboardButton("Download Link", callback_data=f"finalup_link_{user_id}"),
    ])
    
    buttons.append([
        InlineKeyboardButton("Rename File", callback_data=f"final_rename_{user_id}"),
        InlineKeyboardButton("Zip & Upload", callback_data=f"final_zip_{user_id}"),
    ])
    
    buttons.append([
        InlineKeyboardButton("Cancel & Delete", callback_data=f"cancel_upload_{user_id}"),
    ])
    
    return InlineKeyboardMarkup(buttons)
