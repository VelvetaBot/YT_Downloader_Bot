import sys
import os
import asyncio
import threading
import requests
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- WEB SERVER (Koyeb కోసం) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running via External Website!"

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

# --- WEBSITE DOWNLOADER FUNCTION ---
# మనం 'yt-dlp' వాడకుండా, ఈ వెబ్‌సైట్ (Cobalt) ని వాడుతున్నాం.
def get_video_from_website(url):
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    data = {
        "url": url,
        "vQuality": "720",
        "filenamePattern": "basic"
    }
    
    try:
        response = requests.post(api_url, json=data, headers=headers)
        response_json = response.json()
        
        # వెబ్‌సైట్ నుండి డైరెక్ట్ వీడియో లింక్ వస్తుంది
        if "url" in response_json:
            return response_json["url"]
        else:
            return None
    except Exception as e:
        print(f"Website Error: {e}")
        return None

# --- COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 **Hello! I am ready.**\n\n"
        "Send me a YouTube link, I will fetch it from an external website for you! 🚀"
    )

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    status_msg = await message.reply_text("🔄 **Connecting to External Website...**")

    # 1. వెబ్‌సైట్ నుండి లింక్ తెచ్చుకోవడం
    direct_link = await asyncio.to_thread(get_video_from_website, url)

    if not direct_link:
        await status_msg.edit_text("❌ Website is busy or link is invalid. Try again later.")
        return

    try:
        await status_msg.edit_text("⬇️ **Downloading Video...**")
        
        # 2. ఆ లింక్ నుండి వీడియోని మన సర్వర్‌కి డౌన్లోడ్ చేయడం
        video_file = f"video_{message.from_user.id}.mp4"
        
        def download_file():
            with requests.get(direct_link, stream=True) as r:
                r.raise_for_status()
                with open(video_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        
        await asyncio.to_thread(download_file)

        # 3. టెలిగ్రామ్‌కి అప్‌లోడ్ చేయడం
        if os.path.exists(video_file):
            await status_msg.edit_text("⬆️ **Uploading...**")
            await app.send_video(
                message.chat.id, 
                video=video_file, 
                caption="✅ **Downloaded via External Web!**"
            )
            os.remove(video_file)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Failed to download file.")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

if __name__ == '__main__':
    start_web_server()
    app.run()
        
