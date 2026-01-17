# bot.py - YouTube Downloader Bot with Multiple Fallback Methods

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

⚠️ **Works best with:**
• Music videos
• Short videos (under 15 minutes)
• Popular channel videos
• Non-restricted content

💡 Some videos may fail due to YouTube's strict policies.
"""
    
    keyboard = [[InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

def get_ydl_opts(for_download=False):
    """Get yt-dlp options with multiple extraction methods"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'force_generic_extractor': False,
        'age_limit': 21,
        # Try multiple clients
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android'],
                'skip': ['translated_subs'],
            }
        },
        # Use mobile user agent
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.02.39 (Linux; U; Android 11) gzip',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }
    
    if for_download:
        opts['quiet'] = False
        opts['no_warnings'] = False
    
    return opts

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube URL"""
    if not update.message or not update.message.text:
        return
    
    url = update.message.text.strip()
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link!")
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    processing_msg = await update.message.reply_text("🔍 Checking video...\n⏳ Please wait...")
    
    try:
        # Try multiple extraction methods
        info = None
        methods = [
            {'player_client': ['ios']},
            {'player_client': ['mweb']},
            {'player_client': ['android']},
            {'player_client': ['android', 'ios']},
        ]
        
        for idx, method in enumerate(methods):
            try:
                logger.info(f"Trying method {idx + 1}: {method}")
                opts = get_ydl_opts()
                opts['extractor_args']['youtube'] = method
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                if info:
                    logger.info(f"Success with method {idx + 1}")
                    break
            except Exception as e:
                logger.warning(f"Method {idx + 1} failed: {str(e)[:100]}")
                continue
        
        if not info:
            await processing_msg.edit_text(
                "❌ Could not access this video.\n\n"
                "**Possible reasons:**\n"
                "• Age-restricted content\n"
                "• Members-only video\n"
                "• Geographic restrictions\n"
                "• Very recent upload\n\n"
                "💡 **Try:**\n"
                "• A different video\n"
                "• A popular music video\n"
                "• An older upload (24+ hours)"
            )
            return
        
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        thumbnail = info.get('thumbnail', '')
        uploader = info.get('uploader', 'Unknown')
        
        context.user_data['url'] = url
        context.user_data['title'] = title
        
        keyboard = [
            [InlineKeyboardButton("🎬 Best Quality", callback_data='best')],
            [InlineKeyboardButton("📹 720p", callback_data='720')],
            [InlineKeyboardButton("📱 480p", callback_data='480')],
            [InlineKeyboardButton("🎵 Audio Only", callback_data='audio')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mins = duration // 60 if duration else 0
        secs = duration % 60 if duration else 0
        
        caption = f"✅ **Video Found!**\n\n"
        caption += f"📺 {title}\n"
        caption += f"👤 {uploader}\n"
        caption += f"⏱ {mins}:{secs:02d}\n\n"
        caption += f"✨ Select quality:"
        
        try:
            await processing_msg.delete()
            if thumbnail:
                await update.message.reply_photo(
                    photo=thumbnail,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except:
            await processing_msg.edit_text(
                caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred.\n\n"
            "Please try:\n"
            "• A different video\n"
            "• Waiting 2-3 minutes\n"
            "• A popular/older video"
        )

def progress_hook(d):
    """Progress hook"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        logger.info(f"Downloading: {percent}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('url')
    title = context.user_data.get('title', 'video')
    
    if not url:
        await query.edit_message_caption(caption="❌ Session expired. Send link again.")
        return
    
    download_msg = await query.message.reply_text(
        "⬇️ **Starting download...**\n🔄 This may take a moment...",
        parse_mode='Markdown'
    )
    
    filename = None
    
    try:
        # Format selection
        if quality == 'best':
            format_opt = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]'
        elif quality == '720':
            format_opt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]'
        elif quality == '480':
            format_opt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]'
        elif quality == 'audio':
            format_opt = 'bestaudio[ext=m4a]/bestaudio'
        else:
            format_opt = 'best[height<=720]'
        
        os.makedirs('downloads', exist_ok=True)
        output_template = 'downloads/%(title).50s.%(ext)s'
        
        # Try download with multiple methods
        success = False
        methods = [
            {'player_client': ['ios']},
            {'player_client': ['mweb']},
            {'player_client': ['android']},
        ]
        
        for idx, method in enumerate(methods):
            try:
                logger.info(f"Download attempt {idx + 1}")
                
                opts = get_ydl_opts(for_download=True)
                opts.update({
                    'format': format_opt,
                    'outtmpl': output_template,
                    'progress_hooks': [progress_hook],
                })
                opts['extractor_args']['youtube'] = method
                
                if quality == 'audio':
                    opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                
                await download_msg.edit_text(
                    f"⬇️ **Downloading... (Attempt {idx + 1})**\n📥 Please wait...",
                    parse_mode='Markdown'
                )
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    if quality == 'audio':
                        filename = os.path.splitext(filename)[0] + '.mp3'
                
                if os.path.exists(filename):
                    success = True
                    logger.info(f"Download success with method {idx + 1}")
                    break
                    
            except Exception as e:
                logger.warning(f"Download method {idx + 1} failed: {str(e)[:100]}")
                continue
        
        if not success or not filename or not os.path.exists(filename):
            await download_msg.edit_text(
                "❌ Download failed after multiple attempts.\n\n"
                "This video may have strong restrictions.\n"
                "Try a different video."
            )
            return
        
        # Check file size
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > 2000 * 1024 * 1024:
            await download_msg.edit_text(
                f"❌ File too large ({file_size_mb:.1f}MB).\n"
                "Telegram limit: 2GB\n"
                "Try lower quality."
            )
            os.remove(filename)
            return
        
        # Check minimum size
        if file_size < 1024:  # Less than 1KB
            await download_msg.edit_text("❌ Download failed - file too small.")
            os.remove(filename)
            return
        
        await download_msg.edit_text(
            f"⬆️ **Uploading to Telegram...**\n"
            f"📤 Size: {file_size_mb:.1f}MB\n"
            f"⏳ Please wait...",
            parse_mode='Markdown'
        )
        
        caption_text = f"✅ **Downloaded via @Velveta_YT_Downloader_bot**\n\n📹 {title[:100]}"
        
        # Upload to Telegram
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
        await query.message.reply_text(
            "✅ **Download Complete!** 🎉\n\nEnjoy your video!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await download_msg.edit_text(
            f"❌ Upload failed.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            "The file may be too large or corrupted."
        )
        
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                logger.info("File cleaned up")
            except:
                pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")

async def health_check(request):
    """Health check"""
    return web.Response(text="Bot running! 🚀")

async def start_web_server():
    """Start web server"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server: port {PORT}")

async def start_bot():
    """Start bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    # Update yt-dlp
    try:
        logger.info("Updating yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "yt-dlp"])
        logger.info("yt-dlp updated!")
    except:
        logger.warning("Could not update yt-dlp")
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot started! 🎉")
    
    while True:
        await asyncio.sleep(1)

async def main():
    """Main"""
    await asyncio.gather(start_web_server(), start_bot())

if __name__ == '__main__':
    asyncio.run(main())
