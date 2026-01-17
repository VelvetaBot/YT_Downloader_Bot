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
    return "Velveta Bot (Multi-Server Mode) is Running!"

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
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2]

# --- MULTI-SERVER API FUNCTION ---
def get_download_link(url, quality):
    # 👇 ఐదు వేరు వేరు సర్వర్ లింకులు (Mirrors)
    # బాట్ వీటిని ఒక్కొక్కటిగా ట్రై చేస్తుంది.
    api_instances = [
        "https://api.cobalt.tools/api/json",      # Server 1 (Official)
        "https://co.wuk.sh/api/json",             # Server 2 (Backup)
        "https://cobalt.start.gg/api/json",       # Server 3
        "https://api.server.cobalt.tools/api/json", # Server 4
        "https://dl.khub.moe/api/json"            # Server 5
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    
    v_quality = "720"
    is_audio = False
    if quality == "360": v_quality = "360"
    elif quality == "mp3": is_audio = True

    data = {
        "url": url,
        "vQuality": v_quality,
        "isAudioOnly": is_audio,
    }

    # 👇 Loop: ఒక్కో లింక్ ట్రై చేస్తుంది
    for api_url in api_instances:
        try:
            print(f"Trying Server: {api_url}") # Logs లో కనిపిస్తుంది
            response = requests.post(api_url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                json_data = response.json()
                if "url" in json_data:
                    return json_data["url"] # పని చేస్తే ఇక్కడే ఆగిపోతుంది
        except Exception as e:
            print(f"Failed {api_url}: {e}")
            continue # ఇది పని చేయకపోతే నెక్స్ట్ లింక్ కి వెళ్తుంది

    return None # అన్నీ ఫెయిల్ అయితేనే ఇది వస్తుంది

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

@app.on_callback_query()
async def cb_handler(client, query):
    data = query.data.split("|")
    quality = data[0]
    user_id = int(data[1])

    if query.from_user.id != user_id:
        await query.answer("Not your request!", show_alert=True)
        return

    url = query.message.reply_to_message.text
    await query.message.edit("🔄 **Finding Best Server...**") # Message changed
    
    # Get Link from Multi-Server Logic
    direct_link = await asyncio.to_thread(get_download_link, url, quality)
    
    if not direct_link:
        await query.message.edit("❌ All Servers are Busy. Please try later.")
        return

    filename = f"video_{user_id}.mp4"
    if quality == "mp3": filename = f"audio_{user_id}.mp3"
    
    start_time = time.time()
    
    try:
        def download_file():
            with requests.get(direct_link, stream=True) as r:
                r.raise_for_status()
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        
        await query.message.edit("⬇️ **Downloading...**")
        await asyncio.to_thread(download_file)

        if os.path.exists(filename):
            await query.message.edit("⬆️ **Uploading...**")
            
            donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate", url="https://buymeacoffee.com/VelvetaBots")]])
            caption_text = f"✅ **Downloaded: {quality.upper()}**" if quality == "mp3" else f"✅ **Downloaded: {quality}p**"

            if quality == "mp3":
                await app.send_audio(
                    query.message.chat.id, 
                    audio=filename, 
                    caption=caption_text,
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=donate_btn,
                    progress=progress,
                    progress_args=(query.message, start_time)
                )
            else:
                await app.send_video(
                    query.message.chat.id, 
                    video=filename, 
                    caption=caption_text,
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=donate_btn,
                    progress=progress,
                    progress_args=(query.message, start_time)
                )
            
            os.remove(filename)
            await query.message.delete()
        else:
            await query.message.edit("❌ Download Error.")

    except Exception as e:
        await query.message.edit(f"❌ Error: {e}")

if __name__ == '__main__':
    start_web_server()
    app.run()
