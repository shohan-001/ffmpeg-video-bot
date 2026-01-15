
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.utils.db_handler import get_db

async def open_settings(user_id: int):
    """Generate main settings menu"""
    db = get_db()
    
    # Fetch values
    v_codec = "H265" if await db.get_hevc(user_id) else "H264"
    res = await db.get_resolution(user_id) or "Source"
    if res == "OG": res = "Source"
    
    a_codec = await db.get_audio(user_id) or "AAC"
    if a_codec == 'dd': a_codec = 'AC3'
    
    buttons = [
        [
            InlineKeyboardButton(f"📹 Video Codec: {v_codec}", callback_data="set_video_codec"),
            InlineKeyboardButton(f"🖥 Resolution: {res}", callback_data="set_resolution")
        ],
        [
            InlineKeyboardButton("🔊 Audio Settings", callback_data="open_audio_settings"),
            InlineKeyboardButton("📜 Subtitles", callback_data="open_subtitle_settings")
        ],
        [
            InlineKeyboardButton("©️ Watermark", callback_data="open_watermark_settings"),
            InlineKeyboardButton("⚙️ Advanced", callback_data="open_advanced_settings")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_settings")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

async def video_settings_menu(user_id: int):
    """Video settings sub-menu (Reframed, Tune, etc)"""
    # Simply toggle codecs here or sub-menus?
    # Reference bot has toggle for HEVC
    db = get_db()
    hevc = await db.get_hevc(user_id)
    
    buttons = [
        [
            InlineKeyboardButton(f"H265 (HEVC): {'ON' if hevc else 'OFF'}", callback_data="toggle_hevc")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")
        ]
    ]
    return InlineKeyboardMarkup(buttons)
    
async def resolution_settings_menu(user_id: int):
    """Resolution selection menu"""
    db = get_db()
    current_res = await db.get_resolution(user_id)
    
    resolutions = ['1080', '720', '540', '480', '360', 'OG']
    buttons = []
    row = []
    for r in resolutions:
        text = r if r != 'OG' else 'Source'
        if current_res == r:
            text = f"✅ {text}"
        row.append(InlineKeyboardButton(text, callback_data=f"set_res_{r}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")])
    return InlineKeyboardMarkup(buttons)

async def audio_settings_menu(user_id: int):
    """Audio settings menu"""
    db = get_db()
    # Codec, Channels, Bitrate, SampleRate
    a_codec = await db.get_audio(user_id)
    channels = await db.get_channels(user_id) or "Source"
    
    buttons = [
        [InlineKeyboardButton(f"Codec: {a_codec or 'Source'}", callback_data="set_audio_codec_menu")],
        [InlineKeyboardButton(f"Channels: {channels}", callback_data="set_channels_menu")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)


async def subtitle_settings_menu(user_id: int):
    """Subtitle settings menu"""
    db = get_db()
    soft = await db.get_subtitles(user_id)
    hard = await db.get_hardsub(user_id)
    
    buttons = [
        [InlineKeyboardButton(f"Softsubs (Mux): {'✅' if soft else '❌'}", callback_data="toggle_softsubs")],
        [InlineKeyboardButton(f"Hardsubs (Burn): {'✅' if hard else '❌'}", callback_data="toggle_hardsubs")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

async def watermark_settings_menu(user_id: int):
    """Watermark settings menu"""
    db = get_db()
    enabled = await db.get_watermark(user_id)
    
    buttons = [
        [InlineKeyboardButton(f"Watermark: {'✅' if enabled else '❌'}", callback_data="toggle_watermark")],
        [InlineKeyboardButton("Pos: Bottom Right", callback_data="wm_pos_menu")], # Placeholder for now
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

async def advanced_settings_menu(user_id: int):
    """Advanced settings menu"""
    from bot.utils.db_handler import get_db
    db = get_db()
    dest = "Telegram"
    if db:
        pref = await db.get_default_destination(user_id)
        dest = "Google Drive" if pref == "gdrive" else "Telegram"

    buttons = [
        [InlineKeyboardButton(f"Default Upload: {dest}", callback_data="toggle_default_destination")],
        [InlineKeyboardButton("Reset All Settings", callback_data="reset_settings_confirm")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main_settings")]
    ]
    return InlineKeyboardMarkup(buttons)
