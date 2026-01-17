# bot.py - YouTube Downloader Bot with Enhanced Bot Detection Bypass

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import yt_dlp
import asyncio
from aiohttp import web

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_USERNAME = "@Velvetabots"
PORT = int(os.environ.get('PORT', 10000))

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

⚠️ Note: Some videos may not be available due to YouTube restrictions.
"""
    
    keyboard = [[InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube URL"""
    # Check if message and text exist
    if not update.message or not update.message.text:
        return
    
    url = update.message.text.strip()
    
    # Check if it's a valid YouTube URL
    if 'youtube.com' not in url and 'youtu.be' not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link!")
        return
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Fetch video info with enhanced options
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'no_color': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'geo_bypass': True,
            'age_limit': None,
            # Use multiple methods to extract info
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios', 'tv_embedded'],
                    'skip': ['hls', 'dash'],
                }
            },
            # Enhanced headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                await update.message.reply_text("❌ Could not extract video information. The video might be unavailable.")
                return
            
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            
            # Store URL in context
            context.user_data['url'] = url
            context.user_data['title'] = title
            
            # Create quality options
            keyboard = [
                [InlineKeyboardButton("🎬 Best Quality (MP4)", callback_data='best')],
                [InlineKeyboardButton("📹 High Quality (720p)", callback_data='720')],
                [InlineKeyboardButton("📱 Medium Quality (480p)", callback_data='480')],
                [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data='audio')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            mins = duration // 60 if duration else 0
            secs = duration % 60 if duration else 0
            caption = f"📺 **{title}**\n⏱ Duration: {mins}:{secs:02d}\n\n✨ Select quality:"
            
            if thumbnail:
                try:
                    await update.message.reply_photo(
                        photo=thumbnail,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except:
                    await update.message.reply_text(
                        caption,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
    except yt_dlp.utils.DownloadError as e:
        error_str = str(e)
        logger.error(f"DownloadError: {error_str}")
        
        if "Sign in to confirm" in error_str or "not a bot" in error_str:
            await update.message.reply_text(
                "❌ YouTube blocked this request.\n\n"
                "This can happen when:\n"
                "• YouTube detects automated traffic\n"
                "• The video requires age verification\n"
                "• Geographic restrictions apply\n\n"
                "💡 Try:\n"
                "• A different video\n"
                "• Waiting 2-3 minutes\n"
                "• A public, non-restricted video"
            )
        elif "Private video" in error_str:
            await update.message.reply_text("❌ This video is private and cannot be downloaded.")
        elif "Video unavailable" in error_str:
            await update.message.reply_text("❌ This video is unavailable in this region or has been deleted.")
        else:
            await update.message.reply_text(
                f"❌ Could not fetch video information.\n\n"
                f"Error: {error_str[:150]}\n\n"
                "Please try another video or check if the link is correct."
            )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text(
            "❌ An unexpected error occurred.\n"
            "Please try again or contact support."
        )

def progress_hook(d):
    """Progress hook for yt-dlp"""
    if d['status'] == 'downloading':
        logger.info(f"Downloading: {d.get('_percent_str', 'N/A')}")
    elif d['status'] == 'finished':
        logger.info('Download finished, now converting...')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('url')
    title = context.user_data.get('title', 'video')
    
    if not url:
        await query.edit_message_caption(
            caption="❌ Error: URL not found. Please send the link again."
        )
        return
    
    # Show downloading animation
    download_msg = await query.message.reply_text(
        "⬇️ **Downloading...**\n🔄 Please wait...",
        parse_mode='Markdown'
    )
    
    filename = None
    
    try:
        # Set download options based on quality
        if quality == 'best':
            format_opt = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == '720':
            format_opt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
        elif quality == '480':
            format_opt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'
        elif quality == 'audio':
            format_opt = 'bestaudio[ext=m4a]/bestaudio'
        else:
            format_opt = 'best'
        
        # Create download directory
        os.makedirs('downloads', exist_ok=True)
        output_template = 'downloads/%(title)s.%(ext)s'
        
        ydl_opts = {
            'format': format_opt,
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'progress_hooks': [progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'geo_bypass': True,
            'age_limit': None,
            # Enhanced extraction methods
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios', 'tv_embedded'],
                    'skip': ['hls', 'dash'],
                }
            },
            # Enhanced headers for download
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
        }
        
        # For audio, add postprocessor
        if quality == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If audio, change extension to mp3
            if quality == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'
        
        # Check if file exists
        if not os.path.exists(filename):
            await download_msg.edit_text("❌ Error: Downloaded file not found.")
            return
        
        # Check file size
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > 2000 * 1024 * 1024:  # 2GB limit
            await download_msg.edit_text(
                f"❌ File is too large ({file_size_mb:.1f}MB). Telegram limit is 2GB.\nPlease try a lower quality."
            )
            if os.path.exists(filename):
                os.remove(filename)
            return
        
        # Update message to uploading
        await download_msg.edit_text(
            f"⬆️ **Uploading...**\n📤 Size: {file_size_mb:.1f}MB\n⏳ Please wait...",
            parse_mode='Markdown'
        )
        
        # Send the file
        if quality == 'audio':
            await context.bot.send_chat_action(
                chat_id=query.message.chat_id,
                action=ChatAction.UPLOAD_DOCUMENT
            )
        else:
            await context.bot.send_chat_action(
                chat_id=query.message.chat_id,
                action=ChatAction.UPLOAD_VIDEO
            )
        
        caption_text = f"✅ **Downloaded via @Velveta_YT_Downloader_bot**\n\n📹 {title}"
        
        if quality == 'audio':
            with open(filename, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_file,
                    caption=caption_text,
                    parse_mode='Markdown',
                    read_timeout=300,
                    write_timeout=300
                )
        else:
            with open(filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video_file,
                    caption=caption_text,
                    parse_mode='Markdown',
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300
                )
        
        # Delete the downloading message
        await download_msg.delete()
        
        # Add support button
        keyboard = [[InlineKeyboardButton("☕ Donate / Support", url="https://t.me/Velvetabots")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("✅ Download complete!", reply_markup=reply_markup)
        
    except yt_dlp.utils.DownloadError as e:
        error_str = str(e)
        logger.error(f"Download error: {error_str}")
        
        if "Sign in to confirm" in error_str:
            await download_msg.edit_text(
                "❌ YouTube blocked this download.\n\n"
                "The video may have restrictions.\n"
                "Try a different video."
            )
        else:
            await download_msg.edit_text(f"❌ Download failed: {error_str[:150]}")
            
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        await download_msg.edit_text(f"❌ Error: {str(e)[:150]}")
        
    finally:
        # Clean up the file
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                logger.info(f"Cleaned up file: {filename}")
            except Exception as e:
                logger.error(f"Error cleaning up file: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")

# Web server for Render health checks
async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Start a simple web server for Render"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

async def start_bot():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Initialize and start the application
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot started successfully!")
    
    # Keep the bot running
    while True:
        await asyncio.sleep(1)

async def main():
    """Main function to run both web server and bot"""
    # Start web server and bot concurrently
    await asyncio.gather(
        start_web_server(),
        start_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
