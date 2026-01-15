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

# LINKS
CHANNEL_LINK = "https://t.me/Velvetabots"
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"

# --- 2. INTERNAL WEB SERVER (Keep Alive) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is Running (v9.0 - Auto Fallback)"

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

# --- 6. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n"
        "I can download videos **up to 2GB!** 🚀\n\n"
        "**How to use:**\n"
        "1️⃣ Send a YouTube link 🔗\n"
        "2️⃣ I will SCAN available qualities ✨\n"
        "3️⃣ Select and Download! 📥"
    )
    buttons = [[InlineKeyboardButton("📢 Join Update Channel", url=CHANNEL_LINK)]]
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
    await show_options(message, url)

# --- SHOW OPTIONS (SMART SCANNER) ---
async def show_options(message, url):
    msg = await message.reply_text("🔎 **Scanning Video Qualities...**", quote=True)
    try:
        # Use Android client to see all formats
        opts = {
            'quiet': True, 'noprogress': True, 
            'logger': silent_logger, 
            'cookiefile': 'cookies.txt', 
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        info = await asyncio.to_thread(run_sync_info, opts, url)
        title = info.get('title', 'Video')
        formats = info.get('formats', [])

        available_res = set()
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('height'):
                available_res.add(f['height'])
        
        buttons_list = []
        sorted_res = sorted(list(available_res), reverse=True)
        
        display_res = []
        for r in sorted_res:
            if r in [2160, 1440, 1080, 720, 480, 360]:
                display_res.append(r)
        
        if not display_res and sorted_res:
            display_res.append(sorted_res[0]) 

        for res in display_res:
            buttons_list.append(InlineKeyboardButton(f"🎬 {res}p", callback_data=f"video_{res}"))
        
        keyboard = []
        temp_row = []
        for btn in buttons_list:
            temp_row.append(btn)
            if len(temp_row) == 2:
                keyboard.append(temp_row)
                temp_row = []
        if temp_row:
            keyboard.append(temp_row)

        keyboard.append([InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio_mp3")])

        await msg.delete()
        await message.reply_text(
            f"🎬 **{title}**\n\n👇 **Select Quality:**\n(I only show what is available!)", 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            quote=True
        )
        
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

# --- HELPERS ---
def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(url, download=False)

url_store = {}

# --- HANDLE CALLBACKS (WITH AUTO-FALLBACK) ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    
    stored_data = url_store.get(user_id)
    if not stored_data:
         await query.answer("❌ Link expired. Send again.", show_alert=True)
         return
    
    url = stored_data['url']
    original_msg_id = stored_data['msg_id']

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **STARTING...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    # 1. SETUP INITIAL REQUEST
    target_res = None
    if data == "audio_mp3":
        ydl_fmt = 'bestaudio/best'
        ext = 'mp3'
    else:
        target_res = data.split("_")[1] # e.g. "1080"
        # Try to get EXACT resolution first
        ydl_fmt = f'bestvideo[height={target_res}]+bestaudio/best[height={target_res}]'
        ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': silent_logger, 
        'cookiefile': 'cookies.txt', 
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}, 
        'writethumbnail': True, 'concurrent_fragment_downloads': 5, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
    }
    
    if ext == "mp4": opts['merge_output_format'] = 'mp4'
    else: opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 

    try:
        await status_msg.edit_text(f"📥 **DOWNLOADING {target_res if target_res else 'Audio'}...**\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        
        # --- DOWNLOAD ATTEMPT LOGIC ---
        try:
            # ATTEMPT 1: Strict Quality
            await asyncio.to_thread(run_sync_download, opts, url)
            
            # Check if file exists and is not empty
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                raise Exception("Empty File")

        except Exception as e:
            # ATTEMPT 2: AUTO-FALLBACK (If Exact Quality fails, get BEST available)
            error_msg = str(e)
            print(f"Download Failed: {error_msg}") # Log internal error
            
            await status_msg.edit_text(f"⚠️ **{target_res}p Failed. Getting Best Available Quality...**")
            
            # Change settings to "Best Video" (Fail-safe)
            opts['format'] = 'bestvideo+bestaudio/best'
            if 'merge_output_format' in opts: del opts['merge_output_format'] # Simplify
            
            # Disable cookies if they caused the block
            opts['cookiefile'] = None 
            if 'extractor_args' in opts: del opts['extractor_args']

            # Retry Download
            await asyncio.to_thread(run_sync_download, opts, url)
            
            # If still fails, try basic 'best' (single file)
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                 opts['format'] = 'best'
                 await asyncio.to_thread(run_sync_download, opts, url)


        # --- UPLOAD ---
        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        
        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate / Support", url=DONATE_LINK)]])
        thumb = thumb_path if os.path.exists(thumb_path) else None
        caption_text = "✅ **Download Via @VelvetaYTDownloaderBot**"

        if ext == "mp3":
            await app.send_audio(query.message.chat.id, audio=final_path, thumb=thumb, caption=caption_text, reply_to_message_id=original_msg_id, reply_markup=donate_btn, progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING AUDIO...**"))
        else:
            await app.send_video(query.message.chat.id, video=final_path, thumb=thumb, caption=caption_text, supports_streaming=True, reply_to_message_id=original_msg_id, reply_markup=donate_btn, progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING VIDEO...**"))
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    print("✅ System Starting...")
    app.start()
    print("✅ Bot Started & Connected to Telegram!")
    idle()
    print("✅ Bot Started & Connected to Telegram!")
    idle()
