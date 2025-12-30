#!/usr/bin/env python3
"""Main entry point for the FFmpeg Processor Bot"""

import asyncio
from pyrogram import idle
from bot import bot, LOGGER, MONGO_URI, DATABASE_NAME, OWNER_ID, db
from bot.utils.db_handler import Database

async def main():
    """Main function to start the bot"""
    global db
    
    # Initialize database
    if MONGO_URI:
        try:
            db_instance = Database(MONGO_URI, DATABASE_NAME)
            await db_instance.connect()
            LOGGER.info("Connected to MongoDB successfully")
        except Exception as e:
            LOGGER.error(f"Failed to connect to MongoDB: {e}")
    
    # Import handlers
    from bot.handlers import commands, callbacks, file_handler
    
    # Start the bot
    await bot.start()
    
    bot_info = await bot.get_me()
    LOGGER.info(f"Bot started: @{bot_info.username}")
    
    # Notify owner
    try:
        await bot.send_message(
            OWNER_ID,
            "🚀 <b>FFmpeg Processor Bot Started!</b>\n\n"
            f"<b>Bot:</b> @{bot_info.username}\n"
            "<b>Status:</b> Online ✅"
        )
    except Exception as e:
        LOGGER.warning(f"Could not notify owner: {e}")
    
    await idle()
    
    # Cleanup
    await bot.stop()
    LOGGER.info("Bot stopped")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
