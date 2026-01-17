import sys
import os
import asyncio
import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from keep_alive import keep_alive

# --- 1. SILENT LOGGER (Prevents Crashes) ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass

silent_logger = UniversalFakeLogger()
sys.stdout = silent_logger
sys.stderr = silent_logger

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   
BOT_USERNAME = "@VelvetaYTDownloaderBot"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 3. PROGRESS BAR ---
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
    except:
        pass 

# --- 4. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    text = (
        f"👋 **Hi! I am {BOT_USERNAME}**\n\n"
        "I am now in **Safe Mode**. I will force download videos even if errors occur.\n\n"
        "👇 **Send me a YouTube link!**"
    )
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]]))

# --- 5. LINK HANDLER ---
url_store = {}

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    
    # Direct Buttons - No Pre-check to save time
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Download Video (Auto Best)", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="mp3")]
    ])
    await message.reply_text("👇 **Select Format:**", reply_markup=buttons, quote=True)

# --- 6. DOWNLOAD ENGINE (THE FIX) ---
def run_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    if user_id not in url_store:
        await query.answer("❌ Session expired", show_alert=True)
        return
    
    url = url_store[user_id]['url']
    original_msg_id = url_store[user_id]['msg_id']
    await query.message.delete()
    
    status_msg = await query.message.reply_text("⚡ **Initializing...**")
    filename = f"dl_{user_id}_{int(time.time())}"
    
    # --- PLAN A: HIGH QUALITY (Attempts Merge) ---
    if data == "mp3":
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{filename}.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'quiet': True,
        }
        ext = 'mp3'
    else:
        # VIDEO: Try Best, but if fails, fall back strictly
        opts = {
            'format': 'bestvideo+bestaudio/best', # Try merge first, then best single
            'outtmpl': f'{filename}.%(ext)s',
            'merge_output_format': 'mp4',
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}, # Anti-Bot
        }
        ext = 'mp4'

    final_path = f"{filename}.{ext}"

    try:
        await status_msg.edit_text("📥 **Downloading...**")
        
        # 🟢 TRY DOWNLOADING (PLAN A)
        try:
            await asyncio.to_thread(run_download, opts, url)
        except Exception as e:
            # 🔴 IF PLAN A FAILS -> PLAN B (FORCE SINGLE FILE)
            print(f"Plan A failed: {e}")
            if data != "mp3":
                await status_msg.edit_text("⚠️ HQ Failed. Switching to Standard Quality (Guaranteed)...")
                # This format string 'best[ext=mp4]/best' NEVER fails
                opts['format'] = 'best[ext=mp4]/best' 
                await asyncio.to_thread(run_download, opts, url)

        # Check file
        if not os.path.exists(final_path):
             # Try one last fallback name check (sometimes extensions differ)
             for f in os.listdir('.'):
                 if f.startswith(filename):
                     final_path = f
                     break
        
        if not os.path.exists(final_path):
            raise Exception("Download Failed completely.")

        # UPLOAD
        await status_msg.edit_text("☁️ **Uploading...**")
        start_time = time.time()
        
        if "mp3" in final_path or data == "mp3":
             await app.send_audio(
                query.message.chat.id, audio=final_path, caption=f"✅ via {BOT_USERNAME}",
                progress=progress, progress_args=(status_msg, start_time, "☁️ **Uploading Audio...**")
            )
        else:
             await app.send_video(
                query.message.chat.id, video=final_path, caption=f"✅ via {BOT_USERNAME}",
                supports_streaming=True,
                progress=progress, progress_args=(status_msg, start_time, "☁️ **Uploading Video...**")
            )
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {e}")
    finally:
        # Cleanup
        for f in os.listdir('.'):
            if f.startswith(filename):
                try: os.remove(f)
                except: pass

if __name__ == '__main__':
    keep_alive()
    print("✅ Bot Started (Safe Mode)")
    app.run()
