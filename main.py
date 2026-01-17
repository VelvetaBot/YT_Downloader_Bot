import sys
import os
import asyncio
import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive

# --- 1. SILENT LOGGER (Prevents Crashes) ---
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
    text = (
        f"👋 **Hi! I am {BOT_USERNAME}**\n\n"
        "✅ **Simple Mode Active**\n"
        "I will download videos instantly without errors.\n\n"
        "👇 **Send me a YouTube link!**"
    )
    buttons = [[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 5. LINK HANDLER ---
url_store = {}

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    
    # Simple Buttons to avoid confusion
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Download Video", callback_data="video")],
        [InlineKeyboardButton("🎵 Download Audio", callback_data="mp3")]
    ])
    await message.reply_text("👇 **Select:**", reply_markup=buttons, quote=True)

# --- 6. DOWNLOAD LOGIC ---
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
    
    status_msg = await query.message.reply_text("⚡ **Processing...**")
    filename = f"dl_{user_id}_{int(time.time())}"
    
    # --- 🟢 FAIL-SAFE CONFIGURATION ---
    # We stopped asking for 'bestvideo+bestaudio'.
    # Now we just ask for 'best'. This avoids merging errors completely.
    
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'
        ext = 'mp3'
        post_proc = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    else:
        # VIDEO: Request best single file available (mp4 preferred)
        ydl_fmt = 'best[ext=mp4]/best'
        ext = 'mp4'
        post_proc = [] # No processing, just raw download

    opts = {
        'format': ydl_fmt,
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'writethumbnail': True,
        'postprocessors': post_proc,
        # Fake Android to prevent blocks
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.webp" # Youtube often gives webp thumbnails now

    try:
        await status_msg.edit_text("📥 **Downloading...**")
        
        await asyncio.to_thread(run_download, opts, url)

        # File check logic
        if not os.path.exists(final_path):
            # Sometimes extension changes, find any file starting with filename
            for f in os.listdir('.'):
                if f.startswith(filename) and not f.endswith('.part'):
                    final_path = f
                    break
        
        if not os.path.exists(final_path):
            raise Exception("Download Failed. Try again.")

        await status_msg.edit_text("☁️ **Uploading...**")
        start_time = time.time()
        
        # Check if thumbnail exists, otherwise None
        thumb = None
        for f in os.listdir('.'):
             if f.startswith(filename) and (f.endswith('.jpg') or f.endswith('.webp') or f.endswith('.png')):
                 thumb = f
                 break

        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Support", url=DONATE_LINK)]])

        if "mp3" in final_path or data == "mp3":
             await app.send_audio(
                query.message.chat.id, audio=final_path, thumb=thumb, caption=f"✅ via {BOT_USERNAME}",
                progress=progress, progress_args=(status_msg, start_time, "☁️ **Uploading Audio...**"),
                reply_markup=donate_btn
            )
        else:
             await app.send_video(
                query.message.chat.id, video=final_path, thumb=thumb, caption=f"✅ via {BOT_USERNAME}",
                supports_streaming=True,
                progress=progress, progress_args=(status_msg, start_time, "☁️ **Uploading Video...**"),
                reply_markup=donate_btn
            )
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {e}")
    finally:
        # Clean up all files with that ID
        for f in os.listdir('.'):
            if f.startswith(filename):
                try: os.remove(f)
                except: pass

if __name__ == '__main__':
    keep_alive()
    print("✅ Bot Started (Simple Mode)")
    app.run()
