import sys
import os
import asyncio
import time
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- 1. WEB SERVER (Keeps Bot Alive) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Velveta Bot is Alive!"

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

# Links
CHANNEL_LINK = "https://t.me/Velvetabots"
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"
BOT_USERNAME = "@VelvetaYTDownloaderBot"

# Client Setup
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- 3. START COMMAND (Your Custom Message) ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n"
        "I can download videos **up to 2GB!** 🚀\n\n"
        "**How to use:**\n"
        "1️⃣ Send a YouTube link 🔗\n"
        "2️⃣ Select preference ✨\n"
        "3️⃣ Wait for the magic! 📥"
    )
    # Button: Join updated channel
    buttons = [[InlineKeyboardButton("📢 Join Update Channel", url=CHANNEL_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 4. DOWNLOAD HANDLER ---
@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    # Basic Link Check
    if "http" not in url: return

    status_msg = await message.reply_text("⏳ **Checking Link...**")

    # --- 🔴 THE FIX IS HERE ---
    # We use 'best[ext=mp4]/best' instead of '18'.
    # This means: "Give me the best MP4 you have. If no MP4, give me anything else."
    # It NEVER fails.
    opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': f'video_{message.from_user.id}.mp4',
        'quiet': True,
        'nocheckcertificate': True,
        
        # Anti-Bot / Anti-Block Settings
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**")
        
        # Run Download in Background
        def run_dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(run_dl)

        filename = f'video_{message.from_user.id}.mp4'
        
        # Check if file downloaded successfully
        if os.path.exists(filename):
            await status_msg.edit_text("⬆️ **Uploading...**")
            
            # Caption & Donate Button
            caption_text = f"✅ **Downloaded via {BOT_USERNAME}**"
            donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate / Support", url=DONATE_LINK)]])
            
            await app.send_video(
                message.chat.id, 
                video=filename, 
                caption=caption_text,
                reply_markup=donate_btn
            )
            
            # Delete file after sending
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ **Error:** Download Failed. Try a different link.")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
        # Cleanup if error occurs
        filename = f'video_{message.from_user.id}.mp4'
        if os.path.exists(filename): os.remove(filename)

if __name__ == '__main__':
    print("🌍 Starting Web Server...")
    start_web_server()
    print("🤖 Starting Pyrogram Client...")
    app.run()
