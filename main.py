import sys
import os
import time
import math
import asyncio
import threading
import requests
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Velveta Bot (Website Mode) is Alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def start_web_server():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- CONFIG ---
API_ID = 11253846
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a"
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- PROGRESS ANIMATION ---
async def progress(current, total, message, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = time_formatter(elapsed_time)
        estimated_total_time = time_formatter(estimated_total_time)

        progress = "[{0}{1}] \n**Progress**: {2}%\n".format(
            ''.join(["■" for i in range(math.floor(percentage / 10))]),
            ''.join(["□" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2))

        tmp = progress + "**Completed**: {0} of {1}\n**Speed**: {2}/s\n**ETA**: {3}".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(f"⬇️ **Downloading...**\n{tmp}")
        except:
            pass

def humanbytes(size):
    if not size: return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(hours, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2]

# --- API FUNCTION (Cobalt/Website) ---
def get_download_link(url, quality):
    # మనం కుక్కీస్ బదులు API వాడుతున్నాం
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Quality Setup
    v_quality = "720"
    is_audio = False
    
    if quality == "360":
        v_quality = "360"
    elif quality == "mp3":
        is_audio = True

    data = {
        "url": url,
        "vQuality": v_quality,
        "isAudioOnly": is_audio,
    }
    
    try:
        response = requests.post(api_url, json=data, headers=headers)
        data = response.json()
        if "url" in data:
            return data["url"]
        else:
            return None
    except:
        return None

# --- COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n"
        "I can download videos up to 2GB! 🚀\n\n"
        "**How to use:**\n"
        "1️⃣ Send a YouTube link 🔗\n"
        "2️⃣ Select Quality ✨\n"
        "3️⃣ Wait for the magic! 📥"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Join update channel", url="https://t.me/VelvetaBots")]])
    await message.reply_text(welcome_text, reply_markup=buttons)

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    # Quality Buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 720p (HD)", callback_data=f"720|{message.from_user.id}")],
        [InlineKeyboardButton("🎥 360p (SD)", callback_data=f"360|{message.from_user.id}")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"mp3|{message.from_user.id}")]
    ])
    
    await message.reply_text(
        "**Select Quality:** ✨\nchoose one option below:",
        reply_markup=buttons,
        quote=True
    )

# --- CALLBACK HANDLER ---
@app.on_callback_query()
async def cb_handler(client, query):
    data = query.data.split("|")
    quality = data[0]
    user_id = int(data[1])

    if query.from_user.id != user_id:
        await query.answer("Not your request!", show_alert=True)
        return

    url = query.message.reply_to_message.text
    await query.message.edit("🔄 **Connecting to Website...**")
    
    # 1. Get Link from Website API
    direct_link = await asyncio.to_thread(get_download_link, url, quality)
    
    if not direct_link:
        await query.message.edit("❌ Website is busy/error. Try again later.")
        return

    # 2. Download to Server
    filename = f"video_{user_id}.mp4"
    if quality == "mp3": filename = f"audio_{user_id}.mp3"
    
    start_time = time.time()
    
    try:
        def download_file():
            with requests.get(direct_link, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(filename, 'wb') as f:
                    for chunk in
    
