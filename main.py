import sys
import os
import asyncio
import time
import threading
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- 1. WEB SERVER (KEEPS BOT ALIVE) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Velveta Bot is Online! 🌟"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def start_web_server():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

CHANNEL_LINK = "https://t.me/Velvetabots"
BOT_USERNAME = "@VelvetaYTDownloaderBot"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

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
        f"👋 **Hello! I am {BOT_USERNAME}**\n\n"
        "✅ **Status: Anti-Block Active**\n"
        "I am mimicking an Android device to bypass errors.\n\n"
        "👇 **Send me a YouTube link!**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]])
    )

# --- 5. LINK HANDLER ---
url_store = {}

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Video (Auto Best)", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio (Music)", callback_data="audio")]
    ])
    await message.reply_text("👇 **Select Format:**", reply_markup=buttons, quote=True)

# --- 6. DOWNLOAD ENGINE ---
def run_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    
    if user_id not in url_store:
        await query.answer("❌ Session expired.", show_alert=True)
        return
    
    url = url_store[user_id]['url']
    await query.message.delete()
    
    status_msg = await query.message.reply_text("⚡ **Spoofing Android Client...**")
    filename = f"dl_{user_id}_{int(time.time())}"

    if data == "audio":
        ydl_fmt = 'bestaudio[ext=m4a]/bestaudio/best'
        ext = 'm4a'
        upload_func = app.send_audio
        type_str = "Audio"
    else:
        # Video: Direct download only (Safe Mode)
        ydl_fmt = 'best[ext=mp4]/best'
        ext = 'mp4'
        upload_func = app.send_video
        type_str = "Video"

    # --- 🔴 ANTI-BLOCK SETTINGS ---
    opts = {
        'format': ydl_fmt,
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        
        # 1. Force IPv4 (Koyeb IPv6 is often blocked)
        'force_ipv4': True,
        
        # 2. Spoof Android Client (This fixes "Empty File")
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        
        # 3. Use Cookies (Must exist in repo)
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }

    final_path = f"{filename}.{ext}"
    
    try:
        await status_msg.edit_text(f"⬇️ **Downloading {type_str}...**")
        await asyncio.to_thread(run_download, opts, url)

        # File Discovery
        if not os.path.exists(final_path):
             for f in os.listdir('.'):
                 if f.startswith(filename) and not f.endswith('.jpg'):
                     final_path = f
                     break
        
        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
             raise Exception("YouTube Blocked the Download (Empty File).")

        await status_msg.edit_text(f"⬆️ **Uploading {type_str}...**")
        start_time = time.time()
        
        await upload_func(
            query.message.chat.id, 
            final_path, 
            caption=f"✅ **Downloaded via {BOT_USERNAME}**",
            progress=progress, 
            progress_args=(status_msg, start_time, f"⬆️ **Uploading {type_str}...**")
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(filename):
                try: os.remove(f)
                except: pass

# --- 7. MAIN LOOP ---
async def main():
    print("🌍 Starting Web Server...")
    start_web_server()
    print("🤖 Starting Bot Client...")
    await app.start()
    print("✅ Bot is Running with Anti-Block!")
    await idle()
    await app.stop()

if __name__ == '__main__':
    app.run(main())
