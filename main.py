import sys
import os
import asyncio
import time
import imageio_ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import yt_dlp
from keep_alive import keep_alive  

# --- 1. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"
CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   
BOT_USERNAME = "@VelvetaYTDownloaderBot"

# --- 2. SILENT LOGGER (Prevents Console Spam) ---
class UniversalFakeLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def info(self, msg): pass

silent_logger = UniversalFakeLogger()
sys.stdout = open(os.devnull, 'w') # Mute Standard Output

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 3. PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        if (now - start_time) % 5 == 0 or current == total:
            percentage = current * 100 / total
            bar = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))
            text = f"{status_text}\n{bar} **{round(percentage)}%**"
            if message.text != text: await message.edit_text(text)
    except: pass 

# --- 4. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"👋 **Hi! I am {BOT_USERNAME}**\nSend me a YouTube link to download!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]])
    )

# --- 5. HANDLE LINK ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    if "youtube.com" not in url and "youtu.be" not in url: return
    
    msg = await message.reply_text("🔎 **Checking...**")
    global url_store
    
    # Simple check to get title
    try:
        with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
    except:
        title = "YouTube Video"

    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    await msg.delete()
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 1080p", callback_data="1080"), InlineKeyboardButton("📀 720p", callback_data="720")],
        [InlineKeyboardButton("📱 360p", callback_data="360"), InlineKeyboardButton("🎧 MP3", callback_data="mp3")]
    ])
    await message.reply_text(f"🎬 **{title}**", reply_markup=buttons)

url_store = {}

# --- 6. DOWNLOAD HELPER ---
def download_video(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

# --- 7. CALLBACK (The Important Part) ---
@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    data = query.data
    store = url_store.get(user_id)
    if not store: return await query.answer("❌ Expired", show_alert=True)
    
    url = store['url']
    await query.message.delete()
    status_msg = await query.message.reply_text("⚡ **Starting...**")
    
    filename = f"vid_{user_id}_{int(time.time())}"
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe() # GET FFMPEG PATH

    # --- CONFIGURATION ---
    opts = {
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True,
        'cookiefile': 'cookies.txt', # Remove if you don't have the file
        'ffmpeg_location': ffmpeg_path, # POINT TO FFMPEG
        'concurrent_fragment_downloads': 5
    }

    # Format Logic
    if data == "mp3":
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
        ext = 'mp3'
    elif data == "1080":
        opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        opts['merge_output_format'] = 'mp4'
        ext = 'mp4'
    elif data == "720":
        opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        opts['merge_output_format'] = 'mp4'
        ext = 'mp4'
    else:
        opts['format'] = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'
        opts['merge_output_format'] = 'mp4'
        ext = 'mp4'

    # --- THE DOWNLOAD LOOP (WITH RESCUE MODE) ---
    try:
        await status_msg.edit_text("📥 **Downloading (High Quality)...**")
        await asyncio.to_thread(download_video, opts, url)
    
    except Exception as e:
        # 🚨 RESCUE MODE: If High Quality fails, use 'best' (Single File)
        print(f"HQ Failed: {e}. Switching to Standard Quality.")
        if data != "mp3":
            try:
                await status_msg.edit_text("⚠️ **HQ Failed. Trying Standard Quality...**")
                # Remove complex settings that need FFmpeg
                opts['format'] = 'best[ext=mp4]/best' 
                opts.pop('merge_output_format', None)
                
                # Retry Download
                await asyncio.to_thread(download_video, opts, url)
            except Exception as final_e:
                await status_msg.edit_text(f"❌ Failed: {final_e}")
                return

    # --- UPLOAD ---
    final_file = f"{filename}.{ext}"
    if os.path.exists(final_file):
        await status_msg.edit_text("☁️ **Uploading...**")
        start_t = time.time()
        try:
            if data == "mp3":
                await app.send_audio(query.message.chat.id, audio=final_file, caption=f"✅ via {BOT_USERNAME}", progress=progress, progress_args=(status_msg, start_t, "Uploading"))
            else:
                await app.send_video(query.message.chat.id, video=final_file, caption=f"✅ via {BOT_USERNAME}", progress=progress, progress_args=(status_msg, start_t, "Uploading"))
            await status_msg.delete()
        except Exception as up_e:
            await status_msg.edit_text(f"⚠️ Upload Error: {up_e}")
        
        os.remove(final_file) # Cleanup
    else:
        await status_msg.edit_text("❌ File not found after download.")

if __name__ == '__main__':
    keep_alive()
    app.run()
