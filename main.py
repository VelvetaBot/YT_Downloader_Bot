import sys
import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- 1. WEB SERVER (Koyeb కోసం) ---
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

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- 3. COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "🌟 **Velveta Downloader (Anti-Bot Mode) Ready!**\n\n"
        "Send me a link, I will try to bypass YouTube protection! 🛡️",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url="https://t.me/Velvetabots")]])
    )

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    status_msg = await message.reply_text("⏳ **Bypassing Bot Detection...**")

    # 👇 ఇదే అసలైన ఫిక్స్ (Android Spoofing)
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': f'video_{message.from_user.id}.mp4',
        'quiet': True,
        'nocheckcertificate': True,
        # మనం ఆండ్రాయిడ్ ఫోన్ లాగా నటిస్తున్నాం
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['web', 'tv']
            }
        }
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**")
        
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(run_download)
        
        filename = f'video_{message.from_user.id}.mp4'

        if os.path.exists(filename):
            await status_msg.edit_text("⬆️ **Uploading...**")
            await app.send_video(
                message.chat.id, 
                video=filename, 
                caption="✅ **Downloaded Successfully!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate", url="https://buymeacoffee.com/VelvetaBots")]])
            )
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Failed: YouTube blocked the request.")

    except Exception as e:
        # ఎర్రర్ వస్తే క్లియర్ గా చూపించు
        await status_msg.edit_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    start_web_server()
    app.run()
