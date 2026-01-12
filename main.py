import sys
import os
import logging
import asyncio
import time
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from keep_alive import keep_alive  

# --- 1. THE UNIVERSAL SILENCER (Fixes ALL Attribute Errors) ---
class UniversalFakeLogger:
    # Standard stream methods (for sys.stdout/stderr)
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False
    
    # Logger methods (for yt-dlp)
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def info(self, msg): pass

# Apply the Silencer to System Outputs
silent_logger = UniversalFakeLogger()
sys.stdout = silent_logger
sys.stderr = silent_logger

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "7523588106:AAHLLbwPCLJwZdKUVL6gA6KNAR_86eHJCWU"

# --- 3. SETUP CLIENT ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- 4. SMART PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            
            filled_blocks = int(percentage / 10)
            bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
            
            current_mb = round(current / 1024 / 1024, 2)
            total_mb = round(total / 1024 / 1024, 2)
            
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**\n📊 {current_mb}MB / {total_mb}MB\n🚀 Speed: {round(speed / 1024 / 1024, 2)} MB/s"
            
            if message.text != text:
                await message.edit_text(text)
                
    except errors.MessageNotModified:
        pass 
    except Exception:
        pass 

# --- START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n"
        "I can download videos **up to 2GB!** 🚀\n\n"
        "**How to use:**\n"
        "1️⃣ Send a YouTube link 🔗\n"
        "2️⃣ Select Quality ✨\n"
        "3️⃣ Wait for the magic! 📥"
    )
    buttons = [[InlineKeyboardButton("📢 Join Update Channel", url="https://t.me/Velvetabots")]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- HANDLE LINKS ---
@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    global url_store
    url_store[user_id] = url
    await show_options(message, url)

# --- SHOW OPTIONS ---
async def show_options(message, url):
    msg = await message.reply_text("🔎 **Checking Link...**")
    try:
        # Use Universal Silencer for logger to fix 'no attribute debug'
        opts = {
            'quiet': True, 
            'noprogress': True,
            'logger': silent_logger,  # <--- FIX IS HERE
            'cookiefile': 'cookies.txt', 
            'source_address': '0.0.0.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
        await msg.delete()
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 1080p", callback_data="1080"), InlineKeyboardButton("🎥 720p", callback_data="720")],
            [InlineKeyboardButton("🎥 360p", callback_data="360"), InlineKeyboardButton("🎵 Audio (MP3)", callback_data="mp3")]
        ])
        await message.reply_text(f"🎬 **{title}**\n\n👇 **Select Quality:**", reply_markup=buttons)
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

url_store = {}

# --- HANDLE BUTTONS ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    
    url = url_store.get(user_id)
    if not url:
         await query.answer("❌ Link expired. Send again.", show_alert=True)
         return

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **STARTING...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    # --- FLEXIBLE FORMATS ---
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'
        ext = 'mp3'
    elif data == "1080":
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        ext = 'mp4'
    elif data == "720":
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        ext = 'mp4'
    else: 
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]'
        ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True,
        'logger': silent_logger, # <--- FIX IS HERE
        'cookiefile': 'cookies.txt', 'source_address': '0.0.0.0',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    if data != "mp3":
        opts['merge_output_format'] = 'mp4'

    if data == "mp3":
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    final_path = f"{filename}.{ext}"

    try:
        await status_msg.edit_text("📥 **DOWNLOADING...**\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        await status_msg.edit_text("☁️ **UPLOADING...**\n(This supports up to 2GB!)")
        start_time = time.time()
        
        if data == "mp3":
            await app.send_audio(query.message.chat.id, audio=final_path, caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", progress=progress, progress_args=(start_time, "☁️ **UPLOADING AUDIO...**"))
        else:
            await app.send_video(query.message.chat.id, video=final_path, caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", supports_streaming=True, progress=progress, progress_args=(start_time, "☁️ **UPLOADING VIDEO...**"))
            
        await status_msg.delete()

    except Exception as e:
        # Ignore ALL logging-related errors
        if "NoneType" in str(e) or "FakeWriter" in str(e):
            pass
        else:
            await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path):
            os.remove(final_path)

if __name__ == '__main__':
    keep_alive()
    print("✅ Bot Started (Universal Silencer Mode)")
    app.run()
