import os
import sys
import asyncio
import time
import logging
import threading
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- 1. CONFIGURATION ---
API_ID = 11253846
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a"
BOT_TOKEN = "8034075115:AAG1mS-FAopJN3TykUBhMWtE6nQOlhBsKNk"

CHANNEL_LINK = "https://t.me/Velvetabots"
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"

# --- 2. INTERNAL WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is Running (v25.0 - Scan Bypass)"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# --- 3. THE SILENCER ---
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

# --- 4. SETUP CLIENT ---
logging.basicConfig(level=logging.INFO)
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=False)

# --- 5. PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            filled_blocks = int(percentage / 10)
            bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
            current_mb = round(current / 1024 / 1024, 2)
            total_mb = round(total / 1024 / 1024, 2)
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**\n📊 {current_mb}MB / {total_mb}MB"
            if message.text != text:
                await message.edit_text(text)
    except Exception:
        pass

# --- 6. COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n\n"
        "**System Status:** Scan Bypass Active 🛡️\n"
        "I will force download even if YouTube blocks scanning!"
    )
    buttons = [[InlineKeyboardButton("📢 Join Update Channel", url=CHANNEL_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    if "youtube.com" not in url and "youtu.be" not in url: return
    
    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    await show_options(message, url)

# --- 7. SHOW OPTIONS (WITH FALLBACK) ---
async def show_options(message, url):
    msg = await message.reply_text("🔎 **Scanning Link...**", quote=True)
    
    try:
        # Try to scan normally first
        opts = {
            'quiet': True, 
            'noprogress': True, 
            'logger': silent_logger,
            'cookiefile': 'cookies.txt',
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }
        info = await asyncio.to_thread(run_sync_info, opts, url)
        title = info.get('title', 'Video')

        resolutions = [2160, 1440, 1080, 720, 480, 360, 240, 144]
        buttons_list = []
        for res in resolutions:
            label = f"🎬 {res}p" if res not in [2160, 1440] else f"🎬 {'4K' if res==2160 else '2K'}"
            data = "warn_144" if res == 144 else f"video_{res}"
            buttons_list.append(InlineKeyboardButton(label, callback_data=data))
        
        keyboard = [buttons_list[i:i+2] for i in range(0, len(buttons_list), 2)]
        keyboard.append([InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio_mp3")])

        await msg.delete()
        await message.reply_text(f"🎬 **{title}**", reply_markup=InlineKeyboardMarkup(keyboard), quote=True)
    
    except Exception:
        # FALLBACK: If scanning fails, show buttons ANYWAY
        await msg.delete()
        fallback_buttons = [
            [InlineKeyboardButton("🎬 1080p", callback_data="video_1080"), InlineKeyboardButton("🎬 720p", callback_data="video_720")],
            [InlineKeyboardButton("🎬 360p", callback_data="video_360"), InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio_mp3")]
        ]
        await message.reply_text(
            f"⚠️ **Scan Blocked, Force Mode Active!**\n\n👇 **Select Quality:**", 
            reply_markup=InlineKeyboardMarkup(fallback_buttons), 
            quote=True
        )

def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(url, download=False)

url_store = {}

# --- 8. DOWNLOAD HANDLER ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    stored = url_store.get(user_id)
    
    if not stored: return await query.answer("❌ Expired", show_alert=True)
    url = stored['url']
    
    if data == "warn_144":
        await query.message.edit_text("⚠️ **Confirm 144p?**", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes", callback_data="video_144")]]))
        return

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **Initializing...**")
    filename = f"vid_{user_id}_{int(time.time())}"

    if data == "audio_mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    else:
        res = data.split("_")[1]
        # Use simple format to avoid errors
        ydl_fmt = f'bestvideo[height<={res}]+bestaudio/best[height<={res}]/best'; ext = 'mp4'

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg"

    # Try clients in order
    clients_to_try = ['android', 'ios', 'web', 'tv']
    success = False

    try:
        await status_msg.edit_text(f"📥 **DOWNLOADING...**")
        
        for client_name in clients_to_try:
            try:
                opts = {
                    'format': ydl_fmt,
                    'outtmpl': f'{filename}.%(ext)s',
                    'quiet': True, 
                    'noprogress': True, 
                    'logger': silent_logger,
                    'cookiefile': 'cookies.txt', 
                    'extractor_args': {'youtube': {'player_client': [client_name]}},
                    'writethumbnail': True,
                    'concurrent_fragment_downloads': 5,
                    'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
                }
                
                if ext == "mp3": 
                    opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'})
                else:
                    opts['merge_output_format'] = 'mp4'

                await asyncio.to_thread(run_sync_download, opts, url)
                
                if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                    success = True
                    break 
            except:
                continue

        if not success:
            raise Exception("All clients blocked.")

        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        thumb = thumb_path if os.path.exists(thumb_path) else None
        
        if ext == "mp3":
            await app.send_audio(query.message.chat.id, audio=final_path, thumb=thumb, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading..."))
        else:
            await app.send_video(query.message.chat.id, video=final_path, thumb=thumb, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading..."))
        
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path):
            os.remove(final_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

if __name__ == '__main__':
    app.start()
    idle()
