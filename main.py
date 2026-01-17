import sys
import os
import asyncio
import time
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import yt_dlp
from keep_alive import keep_alive  

# --- 1. THE UNIVERSAL SILENCER ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass

silent_logger = UniversalFakeLogger()
sys.stdout = silent_logger
sys.stderr = silent_logger

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

# LINKS
CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   
BOT_USERNAME = "@VelvetaYTDownloaderBot"

# --- 3. SETUP CLIENT ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 4. PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            filled_blocks = int(percentage / 10)
            bar = "▰" * filled_blocks + "▱" * (10 - filled_blocks)
            current_mb = round(current / 1024 / 1024, 2)
            total_mb = round(total / 1024 / 1024, 2)
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**\n📂 {current_mb}MB / {total_mb}MB"
            if message.text != text:
                await message.edit_text(text)
    except Exception:
        pass 

# --- 5. HELPER: COOKIE CHECKER ---
def get_cookie_file():
    if os.path.exists('cookies.txt'):
        return 'cookies.txt'
    return None

# --- 6. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        f"👋 **Hello! I am {BOT_USERNAME}**\n\n"
        "I am fixed and ready to download High Quality videos!\n\n"
        "**🚀 Capabilities:**\n"
        "• 1080p / 720p / 360p / MP3\n"
        "• Anti-Block System Active ✅\n\n"
        "**⚡ Just send me a YouTube link!**"
    )
    buttons = [[InlineKeyboardButton("📢 Updates Channel", url=CHANNEL_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 7. HANDLE DOWNLOADS ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    
    # Analyze Video Info
    msg = await message.reply_text("🔎 **Analyzing Link...**", quote=True)
    try:
        # Initial Info Extraction Options
        opts = {
            'quiet': True, 'noprogress': True, 'logger': silent_logger,
            'cookiefile': get_cookie_file(),
            # TRICK YOUTUBE: Pretend to be Android to avoid empty file errors
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        info = await asyncio.to_thread(run_sync_info, opts, url)
        title = info.get('title', 'Video')
        
        await msg.delete()
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 1080p", callback_data="1080"), InlineKeyboardButton("📀 720p", callback_data="720")],
            [InlineKeyboardButton("📱 360p", callback_data="360"), InlineKeyboardButton("🎧 Audio (MP3)", callback_data="mp3")]
        ])
        
        await message.reply_text(f"🎬 **{title}**\n\n👇 **Select Quality:**", reply_markup=buttons, quote=True)
        
    except Exception as e:
        await msg.edit_text(f"⚠️ **Error:** {e}")

url_store = {}

# --- SYNC FUNCTIONS (Run in Thread) ---
def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

# --- HANDLE BUTTONS ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    
    stored_data = url_store.get(user_id)
    if not stored_data:
         await query.answer("❌ Link expired.", show_alert=True)
         return
    
    url = stored_data['url']
    original_msg_id = stored_data['msg_id']

    await query.message.delete()
    status_msg = await query.message.reply_text("⚡ **Starting Download...**")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    # --- QUALITY SELECTION LOGIC ---
    if data == "mp3":
        # Audio Only
        ydl_fmt = 'bestaudio/best'
        ext = 'mp3'
    elif data == "1080":
        # Try 1080, fallback to best available
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        ext = 'mp4'
    elif data == "720":
        # Try 720, fallback to best available
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        ext = 'mp4'
    else: 
        # 360p
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'
        ext = 'mp4'

    # --- KEY FIX FOR "EMPTY FILE" ERROR ---
    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': silent_logger,
        'cookiefile': get_cookie_file(),
        
        # CRITICAL: Spoof Android Client to bypass throttling/empty files
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'check_formats': True,
        
        'writethumbnail': True, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
        
        # Network Stability
        'concurrent_fragment_downloads': 5, 
        'retries': 10,
        'fragment_retries': 10,
    }
    
    if data != "mp3":
        opts['merge_output_format'] = 'mp4'
    else:
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 

    try:
        await status_msg.edit_text("📥 **Downloading Video...**\n(This may take time for HD)")
        
        # Download
        await asyncio.to_thread(run_sync_download, opts, url)

        # Check if file exists and is not empty
        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
            raise Exception("Download Failed: File is empty (YouTube Blocked). Try MP3 or lower quality.")

        await status_msg.edit_text("☁️ **Uploading to Telegram...**")
        start_time = time.time()
        
        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Support", url=DONATE_LINK)]])
        thumb = thumb_path if os.path.exists(thumb_path) else None

        caption_text = f"✅ **Downloaded via {BOT_USERNAME}**"

        if data == "mp3":
            await app.send_audio(
                query.message.chat.id, 
                audio=final_path, 
                thumb=thumb,
                caption=caption_text, 
                reply_to_message_id=original_msg_id, 
                reply_markup=donate_btn,
                progress=progress, 
                progress_args=(status_msg, start_time, "☁️ **Uploading Audio...**")
            )
        else:
            await app.send_video(
                query.message.chat.id, 
                video=final_path, 
                thumb=thumb,
                caption=caption_text, 
                supports_streaming=True, 
                reply_to_message_id=original_msg_id, 
                reply_markup=donate_btn,
                progress=progress, 
                progress_args=(status_msg, start_time, "☁️ **Uploading Video...**")
            )
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Failed:** {e}")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    keep_alive()
    print(f"✅ Bot Started Successfully")
    app.run()
