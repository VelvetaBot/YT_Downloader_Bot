# bot.py - YouTube Downloader Bot using Cobalt API

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import asyncio
from aiohttp import web
import aiohttp
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = "@Velvetabots"
PORT = int(os.environ.get('PORT', 10000))

# Cobalt API endpoint
COBALT_API = "https://api.cobalt.tools/api/json"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = """
🌟 Welcome to Velveta Downloader (Pro)!
🌟

I can download videos up to 2GB! 🚀

How to use:
1️⃣ Send a YouTube link 🔗
2️⃣ Select Quality ✨
3️⃣ Wait for the magic! 📥

✨ Powered by Cobalt API - Fast & Reliable!
"""
    
    keyboard = [[InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def get_video_info(url):
    """Get video info using Cobalt API"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "url": url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3",
                "isAudioOnly": False,
                "filenamePattern": "basic"
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            async with session.post(COBALT_API, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Cobalt API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

async def download_file(url, filename):
    """Download file from URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=300) as response:
                if response.status == 200:
                    with open(filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                    return True
                return False
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube URL"""
    if not update.message or not update.message.text:
        return
    
    url = update.message.text.strip()
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link!")
        return
    
    # Extract video ID for thumbnail
    video_id = extract_video_id(url)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Show processing message
    processing_msg = await update.message.reply_text("🔍 Processing your video...\n⏳ Please wait...")
    
    try:
        # Get video info from Cobalt
        result = await get_video_info(url)
        
        if not result:
            await processing_msg.edit_text(
                "❌ Could not process this video.\n\n"
                "Please try:\n"
                "• A different video\n"
                "• Checking if the link is correct"
            )
            return
        
        # Check if we got an error from Cobalt
        if result.get('status') == 'error':
            error_text = result.get('text', 'Unknown error')
            await processing_msg.edit_text(f"❌ Error: {error_text}")
            return
        
        # Store data in context
        context.user_data['url'] = url
        context.user_data['video_id'] = video_id
        context.user_data['cobalt_data'] = result
        
        # Create quality options
        keyboard = [
            [InlineKeyboardButton("🎬 Best Quality", callback_data='best')],
            [InlineKeyboardButton("📹 720p", callback_data='720')],
            [InlineKeyboardButton("📱 480p", callback_data='480')],
            [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data='audio')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = f"✅ **Video Ready!**\n\n🔗 Link processed successfully\n\n✨ Select quality to download:"
        
        # Try to show thumbnail
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            try:
                await processing_msg.delete()
                await update.message.reply_photo(
                    photo=thumbnail_url,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except:
                await processing_msg.edit_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await processing_msg.edit_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error handling URL: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred while processing your video.\n"
            "Please try again or use a different link."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('url')
    video_id = context.user_data.get('video_id')
    
    if not url:
        await query.edit_message_caption(caption="❌ Session expired. Please send the link again.")
        return
    
    download_msg = await query.message.reply_text(
        "⬇️ **Processing your request...**\n🔄 Please wait...",
        parse_mode='Markdown'
    )
    
    filename = None
    
    try:
        # Prepare Cobalt API request based on quality
        payload = {
            "url": url,
            "vCodec": "h264",
            "aFormat": "mp3",
            "filenamePattern": "basic"
        }
        
        if quality == 'audio':
            payload["isAudioOnly"] = True
            payload["aFormat"] = "mp3"
        else:
            payload["isAudioOnly"] = False
            if quality == 'best':
                payload["vQuality"] = "max"
            elif quality == '720':
                payload["vQuality"] = "720"
            elif quality == '480':
                payload["vQuality"] = "480"
            else:
                payload["vQuality"] = "720"
        
        await download_msg.edit_text(
            "⬇️ **Downloading...**\n🔄 Getting download link...",
            parse_mode='Markdown'
        )
        
        # Get download link from Cobalt
        async with aiohttp.ClientSession() as session:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            async with session.post(COBALT_API, json=payload, headers=headers, timeout=30) as response:
                if response.status != 200:
                    await download_msg.edit_text("❌ Failed to get download link. Try again.")
                    return
                
                result = await response.json()
        
        # Check result status
        if result.get('status') == 'error':
            error_text = result.get('text', 'Unknown error')
            await download_msg.edit_text(f"❌ Error: {error_text}")
            return
        
        # Get download URL
        download_url = result.get('url')
        if not download_url:
            await download_msg.edit_text("❌ Could not get download link. Try another video.")
            return
        
        await download_msg.edit_text(
            "⬇️ **Downloading...**\n📥 Downloading from server...",
            parse_mode='Markdown'
        )
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        
        # Set filename
        ext = 'mp3' if quality == 'audio' else 'mp4'
        filename = f'downloads/video_{video_id or "download"}.{ext}'
        
        # Download the file
        success = await download_file(download_url, filename)
        
        if not success or not os.path.exists(filename):
            await download_msg.edit_text("❌ Download failed. Please try again.")
            return
        
        # Check file size
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > 2000 * 1024 * 1024:
            await download_msg.edit_text(
                f"❌ File too large ({file_size_mb:.1f}MB).\n"
                "Telegram limit is 2GB. Try a lower quality."
            )
            os.remove(filename)
            return
        
        await download_msg.edit_text(
            f"⬆️ **Uploading...**\n📤 Size: {file_size_mb:.1f}MB\n⏳ Sending to Telegram...",
            parse_mode='Markdown'
        )
        
        caption_text = f"✅ **Downloaded via @Velveta_YT_Downloader_bot**\n\n📹 Your video is ready!"
        
        # Send file
        if quality == 'audio':
            with open(filename, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption=caption_text,
                    parse_mode='Markdown',
                    read_timeout=300,
                    write_timeout=300
                )
        else:
            with open(filename, 'rb') as f:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    caption=caption_text,
                    parse_mode='Markdown',
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300
                )
        
        await download_msg.delete()
        
        keyboard = [[InlineKeyboardButton("☕ Support Us", url="https://t.me/Velvetabots")]]
        await query.message.reply_text(
            "✅ Download complete!\n\nEnjoy your video! 🎉",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except asyncio.TimeoutError:
        await download_msg.edit_text("❌ Download timeout. The video might be too large. Try a shorter video.")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await download_msg.edit_text(f"❌ Error: {str(e)[:150]}\n\nPlease try again.")
        
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                logger.info(f"Cleaned up: {filename}")
            except:
                pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="Bot is running! 🚀")

async def start_web_server():
    """Start web server for health checks"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

async def start_bot():
    """Start the Telegram bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot started successfully! 🎉")
    
    while True:
        await asyncio.sleep(1)

async def main():
    """Main entry point"""
    await asyncio.gather(
        start_web_server(),
        start_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
