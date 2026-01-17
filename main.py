import sys
import os
import time
import math
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp

# --- WEB SERVER (Koyeb కోసం) ---
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

# --- CONFIG ---
API_ID = 11253846
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a"
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- PROGRESS BAR ANIMATION ---
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
    if not size:
        return ""
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

# --- START COMMAND ---
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
    # Join Channel Button
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Join update channel", url="https://t.me/VelvetaBots")]])
    await message.reply_text(welcome_text, reply_markup=buttons)

# --- LINK HANDLER ---
@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    # Quality Selection Buttons (Vidssave Style)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 720p (HD)", callback_data=f"720|{message.from_user.id}")],
        [InlineKeyboardButton("🎥 360p (SD)", callback_data=f"360|{message.from_user.id}")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"mp3|{message.from_user.id}")]
    ])
    
    # Save URL in a temporary way (using message reply context)
    await message.reply_text(
        "**Select Quality:** ✨\nchoose one option below:",
        reply_markup=buttons,
        quote=True # Reply to the link
    )

# --- CALLBACK (BUTTON CLICK) ---
@app.on_callback_query()
async def cb_handler(client, query):
    data = query.data.split("|")
    quality = data[0]
    user_id = int(data[1])

    if query.from_user.id != user_id:
        await query.answer("This is not your request!", show_alert=True)
        return

    # URL ని పాత మెసేజ్ నుండి తీసుకోవడం
    url = query.message.reply_to_message.text
    await query.message.edit("🔄 **Processing...**")
    
    start_time = time.time()

    # Options Setup
    ydl_opts = {
        'cookiefile': 'cookies.txt', # Cookies Required
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'outtmpl': f'download_{user_id}.%(ext)s',
        'extractor_args': {'youtube': {'player_client': ['android']}}, # Android Mode
    }

    # Quality Logic
    if quality == "720":
        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[ext=mp4]'
    elif quality == "360":
        ydl_opts['format'] = '18' # Safe Mode (Best for Errors)
    elif quality == "mp3":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        # Downloading
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        filename = await asyncio.to_thread(run_download)

        # Uploading
        if os.path.exists(filename):
            # Change filename for MP3 if needed
            if quality == "mp3" and not filename.endswith(".mp3"):
                new_name = filename.rsplit(".", 1)[0] + ".mp3"
                if os.path.exists(new_name): filename = new_name

            await query.message.edit("⬆️ **Uploading...**")
            
            # Donate Button
            donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate", url="https://buymeacoffee.com/VelvetaBots")]])

            if quality == "mp3":
                await app.send_audio(
                    query.message.chat.id, 
                    audio=filename, 
                    caption=f"✅ **Downloaded: {quality.upper()}**",
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=donate_btn,
                    progress=progress,
                    progress_args=(query.message, start_time)
                )
            else:
                await app.send_video(
                    query.message.chat.id, 
                    video=filename, 
                    caption=f"✅ **Downloaded: {quality}p**",
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=donate_btn,
                    progress=progress,
                    progress_args=(query.message, start_time)
                )
            
            os.remove(filename)
            await query.message.delete()
        else:
            await query.message.edit("❌ Download Failed.")

    except Exception as e:
        await query.message.edit(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    start_web_server()
    app.run()
    
