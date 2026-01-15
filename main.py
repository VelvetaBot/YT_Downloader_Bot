import os
import sys
import asyncio
import time
import logging
import threading
import re
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
    return "✅ Bot is Running (v20.0 - OAuth2 Mode)"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# --- 3. SMART LOGGER (CAPTURES LOGIN CODE) ---
class OAuthLogger:
    def __init__(self, client, chat_id, msg_id):
        self.client = client
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.code_detected = False

    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    
    def debug(self, msg): self.check_auth(msg)
    def info(self, msg): self.check_auth(msg)
    def warning(self, msg): self.check_auth(msg)
    def error(self, msg): self.check_auth(msg)

    def check_auth(self, msg):
        # YouTube sends a message like: "To give yt-dlp access... go to google.com/device and enter code ABCD-1234"
        if "google.com/device" in msg and not self.code_detected:
            self.code_detected = True
            try:
                # Find the code (e.g., R45G-H78J)
                match = re.search(r'code\s+([A-Z0-9-]+)', msg)
                if match:
                    code = match.group(1)
                    # Send alert to user
                    text = (
                        f"⚠️ **YOUTUBE LOGIN REQUIRED**\n\n"
                        f"YouTube blocked the server. Please authorize it manually:\n\n"
                        f"1️⃣ Tap here: [google.com/device](https://www.google.com/device)\n"
                        f"2️⃣ Enter Code: `{code}`\n\n"
                        f"⏳ **Waiting for you... (Don't close this)**"
                    )
                    # Send update to Telegram safely
                    self.client.loop.create_task(
                        self.client.edit_message_text(
                            chat_id=self.chat_id, 
                            message_id=self.msg_id, 
                            text=text, 
                            disable_web_page_preview=True
                        )
                    )
            except Exception as e:
                print(f"Logger Error: {e}")

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
        "**NOTE:** If I get blocked, I will send you a login code.\n"
        "You must enter it in Google to verify you are human."
    )
    await message.reply_text(welcome_text)

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    if "youtube.com" not in url and "youtu.be" not in url: return
    
    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    await show_options(message, url)

async def show_options(message, url):
    msg = await message.reply_text("🔎 **Scanning...**", quote=True)
    try:
        # Simple scan first
        opts = {'quiet': True, 'extractor_args': {'youtube': {'player_client': ['android']}}}
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
    except Exception as e:
        await msg.edit_text(f"⚠️ **Scan Failed:** {e}")

def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(url, download=False)

url_store = {}

@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    stored = url_store.get(user_id)
    
    if not stored: return await query.answer("❌ Expired", show_alert=True)
    url = stored['url']
    
    if data == "warn_144":
        await query.message.edit_text("⚠️ **144p is blurry. Confirm?**", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes", callback_data="video_144")]]))
        return

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **Initializing...**")
    filename = f"vid_{user_id}_{int(time.time())}"

    if data == "audio_mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    else:
        res = data.split("_")[1]
        ydl_fmt = f'bestvideo[height<={res}]+bestaudio/best/best'; ext = 'mp4'

    # --- OAUTH2 ACTIVATION ---
    custom_logger = OAuthLogger(app, query.message.chat.id, status_msg.id)
    
    opts = {
        'format': ydl_fmt,
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': False, 
        'logger': custom_logger,  # Catches the code
        'username': 'oauth2',     # Forces Login if needed
        'writethumbnail': True,
        'concurrent_fragment_downloads': 5,
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
    }
    
    if ext == "mp3": 
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'})
    else:
        opts['merge_output_format'] = 'mp4'

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg"

    try:
        await status_msg.edit_text(f"📥 **DOWNLOADING...**\n(If stuck, check for login code!)")
        await asyncio.to_thread(run_sync_download, opts, url)
        
        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        thumb = thumb_path if os.path.exists(thumb_path) else None
        
        if ext == "mp3":
            await app.send_audio(query.message.chat.id, audio=final_path, thumb=thumb, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading..."))
        else:
            await app.send_video(query.message.chat.id, video=final_path, thumb=thumb, progress=progress, progress_args=(status_msg, start_time, "☁️ Uploading..."))
        
        await status_msg.delete()
    except Exception as e:
        if "Sign in" in str(e):
            await status_msg.edit_text("❌ **Login Timed Out.** Please try again and enter the code quickly.")
        else:
            await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    app.start()
    idle()
