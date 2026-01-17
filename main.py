import sys
import os
import asyncio
import time
# --- FIX: AUTO-DETECT FFMPEG ---
import imageio_ffmpeg
os.environ['FFMPEG_BINARY'] = imageio_ffmpeg.get_ffmpeg_exe()
# --------------------------------
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

# --- 4. RELIABLE PROGRESS BAR ---
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

# --- 5. GROUP MODERATION ---
@app.on_message(filters.group, group=1)
async def group_moderation(client, message):
    if not message.text: return
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]: return 
    except: pass 
    text = message.text.lower()
    allowed = ["youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com", "tiktok.com"]
    if not any(d in text for d in allowed):
        try: await message.delete()
        except: pass 

# --- 6. HELPER: THREADED DOWNLOAD ---
def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

# --- 7. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        f"👋 **Hello! I am {BOT_USERNAME}**\n\n"
        "Send me a YouTube link to start downloading!\n"
    )
    buttons = [[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 8. HANDLE DOWNLOADS ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    if "youtube.com" not in url and "youtu.be" not in url: return

    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    await show_options(message, url)

# --- SHOW OPTIONS ---
async def show_options(message, url):
    try: msg = await message.reply_text("🔎 **Checking...**", quote=True)
    except: return

    try:
        opts = {'quiet': True, 'noprogress': True, 'logger': silent_logger, 'cookiefile': 'cookies.txt'}
        info = await asyncio.to_thread(run_sync_info, opts, url)
        title = info.get('title', 'Video')
        await msg.delete()
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 1080p", callback_data="1080"), InlineKeyboardButton("📀 720p", callback_data="720")],
            [InlineKeyboardButton("📱 360p", callback_data="360"), InlineKeyboardButton("🎧 MP3", callback_data="mp3")]
        ])
        await message.reply_text(f"🎬 **{title}**", reply_markup=buttons, quote=True)
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

url_store = {}

# --- HANDLE BUTTONS ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    stored_data = url_store.get(user_id)
    if not stored_data: return await query.answer("❌ Expired", show_alert=True)
    
    url = stored_data['url']
    original_msg_id = stored_data['msg_id']
    await query.message.delete()
    status_msg = await query.message.reply_text("⚡ **Starting...**")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    # 1. DEFINE PREFERRED FORMATS
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    elif data == "1080":
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'; ext = 'mp4'
    elif data == "720":
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'; ext = 'mp4'
    else: 
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'; ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': silent_logger,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(), # FORCE FFMPEG PATH
        'writethumbnail': True, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
        'concurrent_fragment_downloads': 5
    }

    if data == "mp3":
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'})
    else:
        opts['merge_output_format'] = 'mp4'

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg"

    try:
        # ATTEMPT 1: High Quality Download
        await status_msg.edit_text("📥 **Downloading...**")
        await asyncio.to_thread(run_sync_download, opts, url)

    except Exception as e:
        # ATTEMPT 2: RESCUE MODE (If 1080p/Merge fails, download standard quality)
        print(f"Merge failed: {e}. Retrying with Standard Quality.")
        if data != "mp3":
            opts['format'] = 'best[ext=mp4]/best' # Single file mode (No FFmpeg needed)
            opts.pop('merge_output_format', None) # Remove merge command
            try:
                await status_msg.edit_text("⚠️ **High Quality Failed. Trying Standard Quality...**")
                await asyncio.to_thread(run_sync_download, opts, url)
            except Exception as e2:
                await status_msg.edit_text(f"❌ Failed: {e2}")
                return

    # UPLOAD SECTION
    if os.path.exists(final_path):
        try:
            await status_msg.edit_text("☁️ **Uploading...**")
            start_time = time.time()
            thumb = thumb_path if os.path.exists(thumb_path) else None
            donate = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Support", url=DONATE_LINK)]])

            if data == "mp3":
                await app.send_audio(query.message.chat.id, audio=final_path, thumb=thumb, caption=f"✅ via {BOT_USERNAME}", reply_markup=donate, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading Audio"))
            else:
                await app.send_video(query.message.chat.id, video=final_path, thumb=thumb, caption=f"✅ via {BOT_USERNAME}", reply_markup=donate, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading Video"))
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Upload Error: {e}")
    else:
        await status_msg.edit_text("❌ Download failed. File not found.")

    # CLEANUP
    if os.path.exists(final_path): os.remove(final_path)
    if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    keep_alive()
    app.run()
