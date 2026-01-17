import sys
import os
import asyncio
import time
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from keep_alive import keep_alive  

# --- 1. THE UNIVERSAL SILENCER (Prevents Crashes) ---
class UniversalFakeLogger:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass

silent_logger = UniversalFakeLogger()
sys.stdout = silent_logger
sys.stderr = silent_logger

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

# 💰 NEW DONATION LINK
SUPPORT_LINK = "https://buymeacoffee.com/VelvetaBots" 

# --- 3. SETUP CLIENT ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=False)

# --- 4. RELIABLE PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 8.00) == 0 or current == total:
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

# --- 5. GROUP MODERATION (Auto-Delete Hi/Welcome & Bad Links) ---
@app.on_message(filters.group, group=1)
async def group_moderation(client, message):
    if not message.text: return
    
    text = message.text.lower()
    
    # A. DELETE GREETINGS (Hi, Hello, Welcome...)
    # We check if the message IS just a greeting or starts with it
    greetings = ["hi", "hello", "hlo", "welcome", "hey", "hii", "hy"]
    if text in greetings or (len(text) < 10 and any(text.startswith(x) for x in greetings)):
        try:
            await message.delete()
            return # Stop here, don't check links
        except:
            pass # Bot might not be Admin

    # B. DELETE NON-YOUTUBE LINKS
    # If it contains "http" but NO "youtube" or "youtu.be"
    if "http" in text:
        if "youtube.com" not in text and "youtu.be" not in text:
            try:
                await message.delete()
                # Optional: Send a warning message that auto-deletes
                # warning = await message.reply("⚠️ **Only YouTube links are allowed here!**")
                # await asyncio.sleep(5)
                # await warning.delete()
            except:
                pass

# --- 6. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader (Pro)!** 🌟\n"
        "I can download videos **up to 2GB!** 🚀\n\n"
        "**How to use:**\n"
        "1️⃣ Send a YouTube link 🔗\n"
        "2️⃣ Select Quality ✨\n"
        "3️⃣ Wait for the magic! 📥"
    )
    buttons = [[InlineKeyboardButton("☕ Donate / Support", url=SUPPORT_LINK)]]
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 7. HANDLE DOWNLOADS (Works in Private & Groups) ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    url = message.text
    user_id = message.from_user.id
    
    # Only process YouTube links
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    
    await show_options(message, url)

# --- SHOW OPTIONS ---
async def show_options(message, url):
    # Reply to the link
    try:
        msg = await message.reply_text("🔎 **Checking Link...**", quote=True)
    except:
        return # If message was deleted by filter, stop

    try:
        opts = {
            'quiet': True, 'noprogress': True, 'logger': silent_logger,
            'cookiefile': 'cookies.txt', 'source_address': '0.0.0.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
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

# --- HANDLE BUTTONS ---
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
    
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    elif data == "1080":
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'; ext = 'mp4'
    elif data == "720":
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]'; ext = 'mp4'
    else: 
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]'; ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': silent_logger,
        'cookiefile': 'cookies.txt', 'source_address': '0.0.0.0',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'writethumbnail': True, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
    }
    
    if data != "mp3":
        opts['merge_output_format'] = 'mp4'
    else:
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 

    try:
        await status_msg.edit_text("📥 **DOWNLOADING...**\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        await status_msg.edit_text("☁️ **UPLOADING...**\n(This supports up to 2GB!)")
        start_time = time.time()
        
        donate_btn = InlineKeyboardMarkup([[InlineKeyboardButton("☕ Donate / Support", url=SUPPORT_LINK)]])
        thumb = thumb_path if os.path.exists(thumb_path) else None

        if data == "mp3":
            await app.send_audio(
                query.message.chat.id, 
                audio=final_path, 
                thumb=thumb,
                caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", 
                reply_to_message_id=original_msg_id, 
                reply_markup=donate_btn,
                progress=progress, 
                progress_args=(status_msg, start_time, "☁️ **UPLOADING AUDIO...**")
            )
        else:
            await app.send_video(
                query.message.chat.id, 
                video=final_path, 
                thumb=thumb,
                caption="✅ **Downloaded via @Velveta_YT_Downloader_bot**", 
                supports_streaming=True, 
                reply_to_message_id=original_msg_id, 
                reply_markup=donate_btn,
                progress=progress, 
                progress_args=(status_msg, start_time, "☁️ **UPLOADING VIDEO...**")
            )
            
        await status_msg.delete()

    except Exception as e:
        if "NoneType" in str(e) or "FakeWriter" in str(e) or "UniversalFakeLogger" in str(e): pass
        else: await status_msg.edit_text(f"⚠️ Error: {e}")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if os.path.exists(thumb_path): os.remove(thumb_path)

if __name__ == '__main__':
    keep_alive()
    print("✅ Bot Started (Group Moderation + Donate)")
    app.run()

