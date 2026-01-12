import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import yt_dlp
from telegram.error import BadRequest, TimedOut, NetworkError

# --- IMPORT KEEP ALIVE (For Render Cloud) ---
from keep_alive import keep_alive  

# --- CONFIGURATION ---
BOT_TOKEN = "7523588106:AAHLLbwPCLJwZdKUVL6gA6KNAR_86eHJCWU"
CHANNEL_ID = -1001840010906
CHANNEL_INVITE_LINK = "https://t.me/Velvetabots"

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- HELPER: CHECK MEMBERSHIP ---
async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        else:
            return False
    except BadRequest:
        return False 
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

# --- 1. START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🌟 **Welcome to Velveta Downloader!** 🌟\n"
        "Your Ultimate YouTube Companion! 🎬✨\n\n"
        "I can help you download:\n"
        "🎥 **High Quality Videos** (1080p, 720p)\n"
        "🎧 **Crystal Clear Audio** (MP3)\n\n"
        "🚀 **How to use me:**\n"
        "1️⃣ Copy a YouTube link 🔗\n"
        "2️⃣ Paste it here 💬\n"
        "3️⃣ Select your quality and enjoy! ⚡\n\n"
        "👇 **Join our update channel to keep this bot free!**"
    )
    user_id = update.effective_user.id
    is_member = await check_membership(user_id, context)
    
    keyboard = []
    if not is_member:
        keyboard.append([InlineKeyboardButton("📢 Join Update Channel", url=CHANNEL_INVITE_LINK)])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# --- 2. HANDLE MESSAGES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text
    chat_id = update.effective_chat.id

    if "youtube.com" not in url and "youtu.be" not in url:
        return

    is_member = await check_membership(user_id, context)

    if not is_member:
        text = (
            f"⚠️ **Hi {update.effective_user.first_name}!**\n\n"
            "🔒 **Access Restricted**\n"
            "To download this video, you must join our channel first.\n\n"
            "👇 **Click below to Join, then try again!**"
        )
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("✅ I Have Joined", callback_data=f'check_join_{user_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['pending_url'] = url
        return

    await show_quality_options(update, context, url)

# --- HELPER: SHOW BUTTONS ---
async def show_quality_options(update, context, url):
    chat_id = update.effective_chat.id
    context.user_data['current_url'] = url
    
    status = await context.bot.send_message(chat_id=chat_id, text="🔎 **Searching for video details...** ⏳")
    
    try:
        # OPTIONS FOR METADATA FETCH
        opts = {
            'quiet': True, 
            'socket_timeout': 15, 
            'cookiefile': 'cookies.txt',
            'source_address': '0.0.0.0' # Force IPv4
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            context.user_data['video_title'] = title
    except:
        title = "YouTube Video"
        context.user_data['video_title'] = title
        
    await context.bot.delete_message(chat_id=chat_id, message_id=status.message_id)

    keyboard = [
        [InlineKeyboardButton("🎥 1080p (HD)", callback_data='qual_1080'), InlineKeyboardButton("🎥 720p (HD)", callback_data='qual_720')],
        [InlineKeyboardButton("🎥 360p (SD)", callback_data='qual_360'), InlineKeyboardButton("🎥 144p (Low)", callback_data='qual_144')],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data='qual_mp3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🎬 **{title}**\n\n✨ **Select your preferred quality:**", 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

# --- 3. HANDLE BUTTON CLICKS ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if data.startswith('check_join_'):
        is_member = await check_membership(user_id, context)
        if is_member:
            await query.answer("✅ Verified! Welcome back.")
            await query.delete_message()
            pending_url = context.user_data.get('pending_url')
            if pending_url:
                await show_quality_options(update, context, pending_url)
            else:
                await context.bot.send_message(chat_id=chat_id, text="✅ **Verified!** Send me a link now! 🚀")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)

    elif data.startswith('qual_'):
        await query.answer()
        url = context.user_data.get('current_url')
        if not url:
            await context.bot.send_message(chat_id=chat_id, text="❌ **Link Expired.** Please send it again.")
            return

        # --- BIG TEXT START ---
        status_msg = await query.edit_message_text(
            text="⏳ **STARTING...**\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%", 
            parse_mode='Markdown'
        )

        quality_map = {
            'qual_1080': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'qual_720': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'qual_360': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'qual_144': 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'qual_mp3': 'bestaudio/best'
        }
        
        chosen_format = quality_map.get(data)
        filename = f"velveta_{chat_id}_{query.message.message_id}"
        
        # --- THE FIX: ADDED IPv4 FORCING ---
        ydl_opts = {
            'format': chosen_format,
            'outtmpl': f'{filename}.%(ext)s',
            'quiet': True,
            'socket_timeout': 60,
            'cookiefile': 'cookies.txt',  # Use ID Card
            'source_address': '0.0.0.0',  # Force IPv4 (Helps bypass blocks)
        }
        
        file_ext = 'mp4'
        if data == 'qual_mp3':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            file_ext = 'mp3'

        final_file = f"{filename}.{file_ext}"

        try:
            # --- BIG TEXT DOWNLOAD ---
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=status_msg.message_id, 
                text="📥 **DOWNLOADING...**\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%", 
                parse_mode='Markdown'
            )

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # CHECK SIZE AND UPLOAD
            if os.path.getsize(final_file) > 50 * 1024 * 1024:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=status_msg.message_id,
                    text="❌ **File too large (>50MB).**\nTelegram limits bots to 50MB uploads. Please choose a lower quality."
                )
            else:
                caption = "✅ **Download Complete!**\n🤖 @Velveta_YT_Downloader_bot"
                
                # --- BIG TEXT UPLOAD ---
                sent = False
                for attempt in range(1, 4):
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=status_msg.message_id,
                            text=f"☁️ **UPLOADING...**\n🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%\n(Attempt {attempt}/3)", 
                            parse_mode='Markdown'
                        )
                        
                        with open(final_file, 'rb') as f:
                            if data == 'qual_mp3':
                                await context.bot.send_audio(
                                    chat_id=chat_id, audio=f, title=context.user_data.get('video_title'), caption=caption,
                                    read_timeout=1200, write_timeout=1200, connect_timeout=1200
                                )
                            else:
                                await context.bot.send_video(
                                    chat_id=chat_id, video=f, caption=caption,
                                    read_timeout=1200, write_timeout=1200, connect_timeout=1200
                                )
                        sent = True
                        break 
                    except (TimedOut, NetworkError):
                        await asyncio.sleep(5)
                        continue

                if sent:
                    await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
                else:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="⚠️ **Failed to upload.**")

        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ **Error:** {e}")
        finally:
            if os.path.exists(final_file):
                os.remove(final_file)

# --- 4. MAIN EXECUTION ---
if __name__ == '__main__':
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(1200).read_timeout(1200).write_timeout(1200).pool_timeout(1200)
        .build()
    )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    
    keep_alive()
    print("✅ Velveta Bot (Fix + Big Text) is Running...")
    application.run_polling()
    
