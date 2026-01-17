import sys
import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running!"

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

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Send me a YouTube link!")

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    status_msg = await message.reply_text("📱 **Using Google Phone Mode...**")

    # 👇 పక్కా ఆండ్రాయిడ్ (Google Phone) సెట్టింగ్స్
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'video_{message.from_user.id}.%(ext)s',
        'cookiefile': 'cookies.txt',  # కొత్త కుక్కీస్ ఉండాలి
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        # ఇది బాట్‌ని "Android Phone" లాగా చూపిస్తుంది
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        }
    }

    try:
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        filename = await asyncio.to_thread(run_download)
        
        if os.path.exists(filename):
            await status_msg.edit_text("⬆️ **Uploading...**")
            await app.send_video(
                message.chat.id, 
                video=filename, 
                caption="✅ **Downloaded via Android Mode**"
            )
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Failed. Cookies might be expired.")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

if __name__ == '__main__':
    start_web_server()
    app.run()
