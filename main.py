import sys
import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from keep_alive import keep_alive  

# --- YOUR CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"
CHANNEL_LINK = "https://t.me/Velvetabots"              
BOT_USERNAME = "@VelvetaYTDownloaderBot"

# --- SYSTEM LOGGING SILENCER ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

sys.stdout = UniversalFakeLogger()
sys.stderr = UniversalFakeLogger()

app = Client("velveta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        if (now - start_time) > 4 or current == total:
            percentage = current * 100 / total
            text = f"{status_text}\n{'🟩' * int(percentage/10)}{'⬜' * (10-int(percentage/10))} **{round(percentage, 1)}%**"
            await message.edit_text(text)
    except:
        pass 

@app.on_message(filters.command("start"))
async def start(client, message):
    text = (f"👋 **Hi {message.from_user.first_name}!**\n\nI am **{BOT_USERNAME}**.\n"
            "⚠️ **Note:** I am currently running in **Safe Mode** (No 1080p merging).\n"
            "Send a link to download!")
    buttons = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "youtu" not in url: return
    
    msg = await message.reply_text("🔎 **Checking Link...**")
    
    # Store URL (Simple Logic)
    global active_urls
    active_urls[message.from_user.id] = url

    # SIMPLIFIED BUTTONS (No quality selection to avoid errors)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Download Video", callback_data="video")],
        [InlineKeyboardButton("🎵 Download Audio", callback_data="mp3")]
    ])
    await msg.edit_text("👇 **Select Format:**", reply_markup=buttons)

active_urls = {}

@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    url = active_urls.get(user_id)
    if not url: return await query.answer("❌ Send link again.")

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **Initializing...**")
    filename = f"dl_{user_id}_{int(time.time())}"

    # --- SAFE MODE CONFIGURATION (NO FFMPEG REQUIRED) ---
    if query.data == "mp3":
        # Best audio only, no conversion
        opts = {'format': 'bestaudio/best', 'outtmpl': f'{filename}.%(ext)s', 'cookiefile': 'cookies.txt'}
        ext_check = "m4a" # usually yt-dlp downloads m4a/webm for audio
    else:
        # Best single file (Video+Audio combined). Usually 720p or 360p.
        opts = {'format': 'best', 'outtmpl': f'{filename}.%(ext)s', 'cookiefile': 'cookies.txt'}
        ext_check = "mp4"

    try:
        await status_msg.edit_text("📥 **Downloading...**")
        await asyncio.to_thread(yt_dlp.YoutubeDL(opts).download, [url])

        # Find the file (extension might vary)
        found_file = None
        for file in os.listdir('.'):
            if file.startswith(filename):
                found_file = file
                break
        
        if not found_file:
            raise Exception("Download failed (Zero bytes).")

        await status_msg.edit_text("☁️ **Uploading...**")
        start_time = time.time()
        caption = f"✅ **Downloaded via {BOT_USERNAME}**"

        if query.data == "mp3":
            await client.send_audio(query.message.chat.id, found_file, caption=caption, 
                                    progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading Audio"))
        else:
            await client.send_video(query.message.chat.id, found_file, caption=caption, 
                                    progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading Video"))

        await status_msg.delete()
        if os.path.exists(found_file): os.remove(found_file)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Error:** {e}")
        # Clean up if possible
        for file in os.listdir('.'):
            if file.startswith(filename): os.remove(file)

if __name__ == '__main__':
    keep_alive()
    app.run()

