import sys
import os
import asyncio
import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive

# --- 1. REMOVED SILENT LOGGER (Let's see the errors!) ---
# We need to see what is happening in the logs.

# --- 2. CONFIGURATION ---
API_ID = 11253846                   
API_HASH = "8db4eb50f557faa9a5756e64fb74a51a" 
BOT_TOKEN = "8034075115:AAHKc9YkRmEgba3Is9dhhW8v-7zLmLwjVac"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=True)

# --- 3. PROGRESS BAR ---
async def progress(current, total, message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            bar = "▓" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
            text = f"{status_text}\n{bar} **{round(percentage, 1)}%**"
            if message.text != text:
                await message.edit_text(text)
    except:
        pass 

# --- 4. START COMMAND ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("🛠️ **Debug Mode Active**\nSend a link. I will tell you EXACTLY what is wrong if it fails.")

# --- 5. SIMPLE DOWNLOAD HANDLER ---
@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client, message):
    url = message.text
    if "http" not in url: return

    msg = await message.reply_text("📝 **Reading Metadata...**")
    
    # Generate unique filename
    filename = f"test_{message.from_user.id}_{int(time.time())}.mp4"
    
    # 🔴 HARDCODED OPTIONS FOR STABILITY
    # We force Format 18 (360p MP4). This exists for 99% of videos.
    opts = {
        'format': '18',  # 360p MP4 (Safest)
        'outtmpl': filename,
        'quiet': False,  # Show errors in logs
        'verbose': True, # Show DETAILED errors
        'cookiefile': 'cookies.txt', # Must exist in repo
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': False,
        # Force IPv4 because Koyeb IPv6 sometimes gets blocked
        'force_ipv4': True, 
    }

    try:
        await msg.edit_text(f"⬇️ **Trying to Download (360p)...**\n`{url}`")
        
        # Run download in thread
        def download_sync():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.download([url])
        
        await asyncio.to_thread(download_sync)
        
        if not os.path.exists(filename):
            await msg.edit_text("❌ **Download Failed:** File not found after download attempt.\nCheck Koyeb Logs.")
            return

        await msg.edit_text("⬆️ **Uploading...**")
        start_time = time.time()
        
        await app.send_video(
            message.chat.id, 
            video=filename, 
            caption="✅ **Test Success (360p)**", 
            progress=progress, 
            progress_args=(msg, start_time, "⬆️ Uploading")
        )
        await msg.delete()

    except Exception as e:
        # PRINT THE ERROR TO USER
        error_text = str(e)
        print(f"ERROR: {error_text}") # Print to Koyeb Console
        await msg.edit_text(f"❌ **CRITICAL ERROR:**\n`{error_text}`")
        
    finally:
        if os.path.exists(filename): 
            os.remove(filename)

if __name__ == '__main__':
    keep_alive()
    print("✅ Debug Bot Started")
    app.run()
