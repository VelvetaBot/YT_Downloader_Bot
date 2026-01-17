import sys
import os
import asyncio
import time
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- 1. WEB SERVER (Koyeb Needs This to Stay Alive) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Velveta Bot is Alive and Running!"

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

# Client Setup
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- 3. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("✅ **Bot Started Successfully!**\nSend me a link to test.")

# --- 4. DOWNLOAD HANDLER ---
@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    status_msg = await message.reply_text("⏳ **Checking...**")

    # DIRECT DOWNLOAD SETTINGS (No Cookies, No FFmpeg)
    opts = {
        'format': '18', # 360p MP4 (Works everywhere)
        'outtmpl': f'video_{message.from_user.id}.mp4',
        'quiet': True,
        'nocheckcertificate': True,
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**")
        
        # Run in thread
        def run_dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(run_dl)

        filename = f'video_{message.from_user.id}.mp4'
        
        if os.path.exists(filename):
            await status_msg.edit_text("⬆️ **Uploading...**")
            await app.send_video(message.chat.id, video=filename, caption="✅ **Download Success**")
            os.remove(filename)
        else:
            await status_msg.edit_text("❌ Download Failed (File not found).")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

if __name__ == '__main__':
    print("🌍 Starting Web Server...")
    start_web_server()
    print("🤖 Starting Pyrogram Client...")
    app.run()
