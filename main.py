import sys
import os
import asyncio
import time
import threading
from flask import Flask
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import yt_dlp

# --- 1. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "7523588106:AAHLLbwPCLJwZdKUVL6gA6KNAR_86eHJCWU"

# LINKS
CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   

# --- 2. INTERNAL WEB SERVER (Keeps Bot Alive) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is Online & Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# Start Web Server in Background Thread
t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# --- 3. THE SILENCER (Prevents Log Spam) ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

# Redirect stdout to silence logs
sys.stdout = UniversalFakeLogger()

# --- 4. SETUP CLIENT ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 5. PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            filled_blocks = int(percentage / 10)
            bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
            current_mb = round(current / 1024 / 1024, 2)
            total_mb = round(total / 1024 / 1024, 2)
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**\n📊 {current_mb}MB / {total_mb}MB"
            if message.text != text:
                await message.edit_text(text)
    except Exception:
        pass 

# --- 6. GROUP MODERATION (STRICT) ---
@app.on_message(filters.group, group=1)
async def group_moderation(client, message):
    # Admin Check
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return 
    except:
        pass 

    content = message.text or message.caption
    if not content:
        try: await message.delete()
        except: pass
        return

    text = content.lower()
    allowed_domains = ["youtube.com", "youtu.be", "twitter.com", "x.com", "instagram
