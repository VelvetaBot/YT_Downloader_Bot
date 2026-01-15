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

# --- 2. INTERNAL WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is Running (v16.0 - Multi-Disguise Mode)"

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
        "2️⃣ I will use **Anti-Block Technology** 🛡️\n"
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

# --- 8. SHOW OPTIONS (MULTI-CLIENT TRY) ---
async def show_options(message, url):
    msg = await message.reply_text("🔎 **Unlocking Video...**", quote=True)
    
    # We define multiple clients to try if one gets blocked
    clients_to_try = [
        ['android'],       # Attempt 1: Android
        ['ios'],           # Attempt 2: iPhone
        ['web'],           # Attempt 3: Web
        ['tv_embedded']    # Attempt 4: TV (Very strong)
    ]
    
    info = None
    last_error = ""

    # Try each client until one works
    for client_type in clients_to_try:
        try:
            opts = {
                'quiet': True, 'noprogress': True, 'logger': silent_logger,
                # NO COOKIES (To avoid Geo-Block)
                'extractor_args': {'youtube': {'player_client': client_type}},
            }
            info = await asyncio.to_thread(run_sync_info, opts, url)
            if info: break # If successful, stop trying
        except Exception as e:
            last_error = str(e)
            continue

    if not info:
        await msg.edit_text(f"⚠️ **All bypass methods failed.**\nYouTube is strictly blocking the server IP.\nError: {last_error}")
        return

    try:
        title = info.get('title', 'Video')
        resolutions = [2160, 1440, 1080, 720, 480, 360, 240, 144]
        
        buttons_list = []
        for res in resolutions:
            if res == 2160: label = "🎬 4K (2160p)"
            elif res == 1440: label = "🎬 2K (1440p)"
            else: label = f"🎬 {res}p"
            
            if res == 144:
                buttons_list.append(InlineKeyboardButton(label, callback_data="warn_144"))
            else:
                buttons_list.append(InlineKeyboardButton(label, callback_data=f"video_{res}"))
        
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
            f"🎬 **{title}**\n\n👇 **Select Preferred Quality:**", 
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

# --- 9. HANDLE CALLBACKS ---
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

    if data == "warn_144":
        warning_text = ("⚠️ **144p Warning**\nVery blurry. Confirm?")
        buttons = [[InlineKeyboardButton("✅ Yes", callback_data="video_144")], [InlineKeyboardButton("🔙 Back", callback_data="back_to_options")]]
        await query.message.edit_text(warning_text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data == "back_to_options":
        await query.message.delete()
        await show_options(client.get_messages(query.message.chat.id, original_msg_id), url)
        return

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **STARTING...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    if data == "audio_mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'; display_res = "Audio"
    else:
        res = data.split("_")[1]; display_res = f"{res}p"
        ydl_fmt = f'bestvideo[height<={res}]+bestaudio/best[height<={res}]/best'; ext = 'mp4'

    # --- ROBUST DOWNLOAD ATTEMPT ---
    # We try multiple clients again for the download phase
    clients_to_try = [['android'], ['ios'], ['tv_embedded']]
    
    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 
    success = False

    try:
        await status_msg.edit_text(f"📥 **DOWNLOADING {display_res}...**\n(Bypassing blocks...)\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        
        for client_type in clients_to_try:
            try:
                opts = {
                    'format': ydl_fmt, 
                    'outtmpl': f'{filename}.%(ext)s',
                    'quiet': True, 'noprogress': True, 'logger': silent_logger, 
                    # NO COOKIES
                    'extractor_args': {'youtube': {'player_client': client_type}},
                    'writethumbnail': True, 'concurrent_fragment_downloads': 5, 
                    'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
                }
                if ext == "mp4": opts['merge_output_format'] = 'mp4'
                else: opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})
                
                await asyncio.to_thread(run_sync_download, opts, url)
                
                if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                    success = True
                    break # It worked!
            except:
                continue # Try next client

        if not success:
            raise Exception("Failed to bypass YouTube block.")

        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        
        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate / Support", url=DONATE_LINK)]])
        thumb = thumb_path if os.path.exists(thumb_path) else None
        caption_text = f"✅ **Download Via @VelvetaYTDownloaderBot**"

        if ext == "mp3":
            await app.send_audio(query.message.chat.id, audio=final_path, thumb=thumb, caption=caption_text, reply_to_message_id=original_msg_id, reply_markup=donate_btn, progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING AUDIO...**"))
        else:
            await app.send_video(query.message.chat.id, video=final_path, thumb=thumb, caption=caption_text, supports_streaming=True, reply_to_message_id=original_msg_id, reply_markup=donate_btn, progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING VIDEO...**"))
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Error: {e}\nTry deleting cookies.txt from GitHub.")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    print("✅ System Starting...")
    app.start()
    print("✅ Bot Started & Connected to Telegram!")
    idle()
