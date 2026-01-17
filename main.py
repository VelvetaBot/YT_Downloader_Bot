import sys
import os
import asyncio
import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive

# --- 1. SILENCE LOGS ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

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
            bar = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**"
            if message.text != text:
                await message.edit_text(text)
    except:
        pass 

# --- 4. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"✅ **Bot is Online!**\nRunning in **Direct Download Mode** (FFmpeg-Free).\n\n👇 **Send a Link:**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]])
    )

# --- 5. LINK HANDLER ---
url_store = {}

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    if "youtube.com" not in url and "youtu.be" not in url: return
    
    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Video (Direct)", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="mp3")]
    ])
    await message.reply_text("👇 **Select:**", reply_markup=buttons, quote=True)

# --- 6. DOWNLOADER ---
def run_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    if user_id not in url_store: return
    
    url = url_store[user_id]['url']
    await query.message.delete()
    status_msg = await query.message.reply_text("⚡ **Starting...**")
    
    filename = f"vid_{user_id}_{int(time.time())}"

    # --- 🔴 THE FIX: STRICTLY NO MERGING ---
    if data == "mp3":
        # Download best audio, but don't fail if conversion fails
        ydl_fmt = 'bestaudio[ext=m4a]/bestaudio/best' 
        ext = 'm4a' # M4A works on Telegram without FFmpeg conversion
    else:
        # VIDEO: Find a file that HAS VIDEO + HAS AUDIO inside it already
        # usually format 18 (360p) or 22 (720p)
        ydl_fmt = 'best[vcodec!=none][acodec!=none]/18/22/best'
        ext = 'mp4'

    opts = {
        'format': ydl_fmt,
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'extractor_args': {'youtube': {'player_client': ['android']}}, # Android spoof
    }

    final_path = f"{filename}.{ext}"

    try:
        await status_msg.edit_text("📥 **Downloading...**")
        await asyncio.to_thread(run_download, opts, url)

        # File Discovery (In case extension changed)
        if not os.path.exists(final_path):
            for f in os.listdir('.'):
                if f.startswith(filename):
                    final_path = f
                    break
        
        if not os.path.exists(final_path): raise Exception("Download failed.")

        await status_msg.edit_text("☁️ **Uploading...**")
        start_time = time.time()
        
        if data == "mp3" or "audio" in final_path:
             await app.send_audio(
                query.message.chat.id, audio=final_path, caption=f"✅ {BOT_USERNAME}",
                progress=progress, progress_args=(status_msg, start_time, "☁️ Audio")
            )
        else:
             await app.send_video(
                query.message.chat.id, video=final_path, caption=f"✅ {BOT_USERNAME}",
                supports_streaming=True,
                progress=progress, progress_args=(status_msg, start_time, "☁️ Video")
            )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(filename): 
                try: os.remove(f)
                except: pass

if __name__ == '__main__':
    keep_alive()
    app.run()
