import sys
import os
import asyncio
import time
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
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
BOT_TOKEN = "8034075115:AAG1mS-FAopJN3TykUBhMWtE6nQOlhBsKNk"

# LINKS
CHANNEL_LINK = "https://t.me/Velvetabots"              
DONATE_LINK = "https://buymeacoffee.com/VelvetaBots"   

# --- 3. SETUP CLIENT ---
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 4. RELIABLE PROGRESS BAR ---
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

# --- 5. GROUP MODERATION (STRICT & SILENT) ---
@app.on_message(filters.group, group=1)
async def group_moderation(client, message):
    # 1. Check if User is Admin (If Admin, Allow EVERYTHING)
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return # Admin message -> Do nothing (Allow)
    except:
        pass 

    # If message has no text (e.g., only photo/video without caption), DELETE it
    if not message.text:
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text.lower()
    
    # 2. Allowed Domains (Twitter, FB, TikTok, YouTube, Instagram)
    allowed_domains = [
        "youtube.com", "youtu.be",  # YouTube
        "twitter.com", "x.com",     # Twitter/X
        "instagram.com",            # Instagram
        "tiktok.com",               # TikTok
        "facebook.com", "fb.watch"  # Facebook
    ]

    # Check if message contains ANY allowed link
    has_allowed_link = any(domain in text for domain in allowed_domains)

    # 3. LOGIC: If NO allowed link is found -> DELETE
    # If allowed link IS found -> Do nothing (Let other bots handle it)
    if not has_allowed_link:
        try:
            await message.delete()
        except:
            pass 

# --- 6. HELPER: THREADED DOWNLOAD ---
def run_sync_download(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])

def run_sync_info(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

# --- 7. START COMMAND (UPDATED) ---
@app.on_message(filters.command("start"))
async def start(client, message):
    # Clean welcome message, no buttons as requested
    welcome_text = (
        "👋 **Hello!**\n\n"
        "Send me a YouTube link to download videos or audio.\n"
        "I support qualities up to 1080p and 2GB files."
    )
    await message.reply_text(welcome_text)

# --- 8. HANDLE DOWNLOADS (PRIVATE CHATS ONLY) ---
@app.on_message(filters.text & ~filters.command("start"), group=2)
async def handle_link(client, message):
    # STRICT RULE: If message is in a GROUP, Ignore it.
    # This ensures this bot acts ONLY as a cleaner in groups, allowing other bots to reply.
    if message.chat.type != ChatType.PRIVATE:
        return

    url = message.text
    user_id = message.from_user.id
    
    # Only process YouTube links in DM
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    global url_store
    url_store[user_id] = {'url': url, 'msg_id': message.id}
    await show_options(message, url)

# --- SHOW OPTIONS ---
async def show_options(message, url):
    try:
        msg = await message.reply_text("🔎 **Processing...**", quote=True)
    except:
        return

    try:
        opts = {
            'quiet': True, 'noprogress': True, 'logger': silent_logger,
            'cookiefile': 'cookies.txt', 'source_address': '0.0.0.0',
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
    status_msg = await query.message.reply_text("⏳ **STARTING...**")
    filename = f"vid_{user_id}_{int(time.time())}"
    
    if data == "mp3":
        ydl_fmt = 'bestaudio/best'; ext = 'mp3'
    elif data == "1080":
        ydl_fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[height<=1080]'; ext = 'mp4'
    elif data == "720":
        ydl_fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]'; ext = 'mp4'
    else: 
        ydl_fmt = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best[height<=360]'; ext = 'mp4'

    opts = {
        'format': ydl_fmt, 
        'outtmpl': f'{filename}.%(ext)s',
        'quiet': True, 'noprogress': True, 'logger': silent_logger,
        'cookiefile': 'cookies.txt', 'source_address': '0.0.0.0',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'writethumbnail': True, 
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
        'concurrent_fragment_downloads': 5, 
        'retries': 10,
        'fragment_retries': 10,
    }
    
    if data != "mp3":
        opts['merge_output_format'] = 'mp4'
    else:
        opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'})

    final_path = f"{filename}.{ext}"
    thumb_path = f"{filename}.jpg" 

    try:
        await status_msg.edit_text("📥 **DOWNLOADING...**")
        
        await asyncio.to_thread(run_sync_download, opts, url)

        await status_msg.edit_text("☁️ **UPLOADING...**")
        start_time = time.time()
        
        # Removed Donate Button from here as well since you requested removal
        thumb = thumb_path if os.path.exists(thumb_path) else None

        if data == "mp3":
            await app.send_audio(
                query.message.chat.id, 
                audio=final_path, 
                thumb=thumb,
                caption="✅ **Downloaded successfully**", 
                reply_to_message_id=original_msg_id, 
                progress=progress, 
                progress_args=(status_msg, start_time, "☁️ **UPLOADING AUDIO...**")
            )
        else:
            await app.send_video(
                query.message.chat.id, 
                video=final_path, 
                thumb=thumb,
                caption="✅ **Downloaded successfully**", 
                supports_streaming=True, 
                reply_to_message_id=original_msg_id, 
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
    print("✅ Bot Started (Strict Mode + Async Fix)")
    app.run()
