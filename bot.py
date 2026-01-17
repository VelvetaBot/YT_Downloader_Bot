# bot.py - YouTube Downloader Bot with Latest yt-dlp fixes

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import yt_dlp
import asyncio
from aiohttp import web
import subprocess
import sys

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

# Update yt-dlp on startup
def update_ytdlp():
    """Update yt-dlp to latest version"""
    try:
        logger.info("Updating yt-dlp to latest version...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        logger.info("yt-dlp updated successfully!")
    except Exception as e:
        logger.error(f"Failed to update yt-dlp: {e}")

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

⚠️ Note: Due to YouTube restrictions, some videos may not work.
Try shorter, public videos for best results!
"""
    
    keyboard = [[InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube URL"""
    if not update.message or not update.message.text:
        return
    
    url = update.message.text.strip()
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link!")
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        # Enhanced yt-dlp options with latest fixes
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            # Force IPv4
            'source_address': '0.0.0.0',
            # Use po_token if available
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web'],
                    'player_skip': ['configs'],
                    'max_comments': [0],
                }
            },
            # Modern browser headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Try to extract info
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                # If extraction fails, try with different client
                logger.warning(f"First extraction attempt failed: {e}")
                ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info = ydl2.extract_info(url, download=False)
            
            if not info:
                await update.message.reply_text("❌ Could not get video information. Please try another video.")
                return
            
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            
            context.user_data['url'] = url
            context.user_data['title'] = title
            
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
                    await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
                
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error: {error_str}")
        
        # User-friendly error messages
        if "Failed to extract" in error_str or "player response" in error_str:
            await update.message.reply_text(
                "❌ YouTube changed something! This happens sometimes.\n\n"
                "💡 **Try these:**\n"
                "• Wait 2-3 minutes and try again\n"
                "• Try a different video (shorter, public videos work better)\n"
                "• Try a popular channel video\n\n"
                "🔄 Bot is using the latest downloader, but YouTube blocks automated downloads frequently."
            )
        elif "Private video" in error_str or "unavailable" in error_str.lower():
            await update.message.reply_text("❌ This video is private or unavailable.")
        elif "Sign in" in error_str:
            await update.message.reply_text(
                "❌ This video requires sign-in (age restriction or members-only).\n"
                "Try a public video without restrictions."
            )
        else:
            await update.message.reply_text(
                f"❌ Error: {error_str[:200]}\n\n"
                "Try a different video or wait a few minutes."
            )

def progress_hook(d):
    """Progress hook for yt-dlp"""
    if d['status'] == 'downloading':
        logger.info(f"Downloading: {d.get('_percent_str', 'N/A')}")
    elif d['status'] == 'finished':
        logger.info('Download finished!')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('url')
    title = context.user_data.get('title', 'video')
    
    if not url:
        await query.edit_message_caption(caption="❌ URL not found. Please send the link again.")
        return
    
    download_msg = await query.message.reply_text("⬇️ **Downloading...**\n🔄 Please wait...", parse_mode='Markdown')
    
    filename = None
    
    try:
        # Format selection
        if quality == 'best':
            format_opt = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == '720':
            format_opt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]'
        elif quality == '480':
            format_opt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]'
        elif quality == 'audio':
            format_opt = 'bestaudio/best'
        else:
            format_opt = 'best'
        
        os.makedirs('downloads', exist_ok=True)
        output_template = 'downloads/%(title)s.%(ext)s'
        
        ydl_opts = {
            'format': format_opt,
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'source_address': '0.0.0.0',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android'],
                    'player_skip': ['configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        }
        
        if quality == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        # Download
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if quality == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
        except Exception as e:
            # Retry with android client only
            logger.warning(f"Download failed, retrying with android client: {e}")
            ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if quality == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
        
        if not os.path.exists(filename):
            await download_msg.edit_text("❌ Download failed. File not found.")
            return
        
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > 2000 * 1024 * 1024:
            await download_msg.edit_text(f"❌ File too large ({file_size_mb:.1f}MB). Try lower quality.")
            os.remove(filename)
            return
        
        await download_msg.edit_text(
            f"⬆️ **Uploading...**\n📤 Size: {file_size_mb:.1f}MB\n⏳ Please wait...",
            parse_mode='Markdown'
        )
        
        caption_text = f"✅ **Downloaded via @Velveta_YT_Downloader_bot**\n\n📹 {title}"
        
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
        
        keyboard = [[InlineKeyboardButton("☕ Support", url="https://t.me/Velvetabots")]]
        await query.message.reply_text("✅ Download complete!", reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await download_msg.edit_text(f"❌ Download failed: {str(e)[:150]}")
        
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Start web server"""
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
        logger.error("BOT_TOKEN not set!")
        return
    
    # Update yt-dlp first
    update_ytdlp()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot started successfully!")
    
    while True:
        await asyncio.sleep(1)

async def main():
    """Main function"""
    await asyncio.gather(
        start_web_server(),
        start_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
