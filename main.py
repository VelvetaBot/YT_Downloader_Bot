import sys
import os
import asyncio
import time
import threading
from flask import Flask
from pyrogram import Client, filters
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
        "✅ **System Status: Stable**\n"
        "I can download Video & Audio safely.\n\n"
        "👇 **Send me a YouTube link!**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url=CHANNEL_LINK)]])
    )

# --- 5. LINK HANDLER ---
url_store = {}

@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    # Basic check
    if "http" not in url: return

    # Store URL for the button click
    url_store[message.from_user.id] = {'url': url, 'msg_id': message.id}
    
    # Show Buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Video (Auto Best)", callback_data="video")],
        [InlineKeyboardButton("🎵 Audio (Music)", callback_data="audio")]
    ])
    await message.reply_text("👇 **Select Format:**", reply_markup=buttons, quote=True)

# --- 6. DOWNLOAD ENGINE ---
def run_download(opts, url):
    with yt_dlp.YoutubeDL(opts)
