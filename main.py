import sys
import os
import asyncio
import time
import threading
import logging
import signal
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import yt_dlp

# --- 1. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
# ✅ NEW TOKEN UPDATED HERE
BOT_TOKEN = "8034075115:AAEW-7eN8fzd31acrcvNwCYwKT2__c6b_ss" 

# LINKS
CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   

# --- 2. INTERNAL WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# --- 3. YT-DLP SILENCER ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass

yt_logger = UniversalFakeLogger()

# --- 4. SETUP CLIENT ---
logging.basicConfig(level=logging.INFO)
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=False)

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

# --- 6. GROUP MODERATION ---
@app.on_message(filters.group, group=1)
async def group_moderation(client, message):
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
    allowed_domains = ["youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com", "tiktok.com", "facebook.com", "fb.watch"]
    
    if not any(domain in text for domain in allowed_domains):
        try: await message.delete()
        except: pass

# --- 7. HELPER FUNCTIONS ---
def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(url, download=False)

# --- 8. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = "🌟 **Welcome to Velveta Downloader!** 🌟\nSend a YouTube link to start! 📥"
    buttons = [[InlineKeyboardButton("📢 Join Update Channel", url=CHANNEL_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 9. HANDLE DOWNLOADS ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    await show_options(message, url)

# --- SHOW OPTIONS ---
async def show_options(message, url):
    try:
        msg = await message.reply_text("🔎 **Checking Link...**", quote=True)
    except:
        return

    try:
        opts = {
            'quiet': True, 'noprogress': True, 'logger': yt_logger,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        info = await asyncio.to_thread(run_sync_info, opts, url)
        title = info.get('title', 'Video')
        
        await msg.delete()
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 1080p", callback_data="1080"), InlineKeyboardButton("🎥 720p", callback_data="720")],
            [InlineKeyboardButton("🎥 360p", callback_data="360"), InlineKeyboardButton("🎵 Audio (MP3)", callback_data="mp3")]
        ])
        
        await message.reply_text(f"🎬 **{title}**\n\n👇 **Select Quality:**", reply_markup=buttons, quote=True)
        
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

url_store = {}

# --- HANDLE BUTTONS (AUTO-REPAIR LOGIC) ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user_id = query.from_user.id
    
    stored_data = url_store.get(user_id)
    if not stored_data:
         await query.answer("❌ Link expired. Send again.", show_alert=True)
         return
    
    url = stored_data['url']
    original_msg_id = stored_data['msg_id']

    await query.message.delete()
    status_msg = await query.message.reply_text("⏳ **STARTING...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    # --- STRATEGY 1: HIGH QUALITY (Merge Video+Audio) ---
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    elif data == "1080":
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'; ext = 'mp4'
    elif data == "720":
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'; ext = 'mp4'
    else: 
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'; ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': yt_logger,
        'cookiefile': 'cookies.txt',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'writethumbnail': True, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
        'concurrent_fragment_downloads': 5, 
    }
    
    if data != "mp3":
        opts['merge_output_format'] = 'mp4'
    else:
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 

    try:
        await status_msg.edit_text("📥 **DOWNLOADING...**\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        
        # Attempt 1: Standard Download
        try:
            await asyncio.to_thread(run_sync_download, opts, url)
        except:
            pass # Fail silently, check file existence below

        # --- STRATEGY 2: FALLBACK (Empty File Fix) ---
        # If file is missing (0 bytes or not found), try simpler method
        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
            await status_msg.edit_text("⚠️ **Merging Failed. Trying Fallback Mode...**")
            
            # Remove complex options
            if 'merge_output_format' in opts: del opts['merge_output_format']
            opts['format'] = 'best' # Download single best file (no merge needed)
            
            await asyncio.to_thread(run_sync_download, opts, url)
            
            # If still failing, raise error
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                raise Exception("Download Failed (File is empty)")

        # Upload
        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        
        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate / Support", url=DONATE_LINK)]])
        thumb = thumb_path if os.path.exists(thumb_path) else None

        if data == "mp3":
            await app.send_audio(
                query.message.chat.id, audio=final_path, thumb=thumb,
                caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", 
                reply_to_message_id=original_msg_id, reply_markup=donate_btn,
                progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING AUDIO...**")
            )
        else:
            await app.send_video(
                query.message.chat.id, video=final_path, thumb=thumb,
                caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", 
                supports_streaming=True, reply_to_message_id=original_msg_id, reply_markup=donate_btn,
                progress=progress, progress_args=(status_msg, start_time, "☁️ **UPLOADING VIDEO...**")
            )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

# --- ROBUST STARTUP ---
def stop_signals(signum, frame):
    print("🔴 Stopping Bot...")
    app.stop()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, stop_signals)
    signal.signal(signal.SIGTERM, stop_signals)
    
    print("✅ System Starting...")
    try:
        app.start()
        print("✅ Bot Started Successfully!")
        idle()
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
