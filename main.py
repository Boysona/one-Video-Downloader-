import shutil
import telebot
import yt_dlp
import os
import uuid
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
from PIL import Image
from io import BytesIO

# BOT SETTINGS
BOT_TOKEN = "8136008912:AAHwM1ZBZ2WxgCnFpRA0MC_EIr9KcRQiF3c"
ADMIN_ID = 5978150981  # Ku beddel ID-gaaga
USER_FILE = "users.txt"
DOWNLOAD_DIR = "downloads"
bot = telebot.TeleBot(BOT_TOKEN)

# CREATE DOWNLOAD DIR
if os.path.exists(DOWNLOAD_DIR):
    shutil.rmtree(DOWNLOAD_DIR)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# SAVE USER
def save_user(user_id):
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w") as f:
            f.write("")
    with open(USER_FILE, "r+") as f:
        ids = f.read().splitlines()
        if str(user_id) not in ids:
            f.write(f"{user_id}\n")

# START COMMAND
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.chat.id
    save_user(user_id)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    text = f"👋 Salam {username}, Send me a TikTok, YouTube, Instagram, Facebook & more link, I’ll download it for you!"
    bot.send_message(user_id, text)

    if user_id == ADMIN_ID:
        show_admin_panel(user_id)

# ADMIN PANEL
def show_admin_panel(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Total Users", "📢 Send Ads (broadcast)")
    bot.send_message(chat_id, "Welcome to Admin Panel", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "📊 Total Users" and msg.chat.id == ADMIN_ID)
def total_users(msg):
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            count = len(f.readlines())
        bot.send_message(msg.chat.id, f"👥 Total users: {count}")
    else:
        bot.send_message(msg.chat.id, "No users yet.")

@bot.message_handler(func=lambda msg: msg.text == "📢 Send Ads (broadcast)" and msg.chat.id == ADMIN_ID)
def ask_broadcast(msg):
    bot.send_message(msg.chat.id, "Send your message (text, photo, video, etc.) to broadcast:")
    bot.register_next_step_handler(msg, broadcast_message)

def broadcast_message(message):
    if not os.path.exists(USER_FILE):
        bot.send_message(message.chat.id, "No users to broadcast to.")
        return

    with open(USER_FILE, "r") as f:
        user_ids = f.read().splitlines()

    sent = 0
    for uid in user_ids:
        try:
            uid = int(uid)
            if message.text:
                bot.send_message(uid, message.text)
            elif message.photo:
                bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                bot.send_video(uid, message.video.file_id, caption=message.caption or "")
            elif message.audio:
                bot.send_audio(uid, message.audio.file_id, caption=message.caption or "")
            elif message.voice:
                bot.send_voice(uid, message.voice.file_id)
            elif message.document:
                bot.send_document(uid, message.document.file_id, caption=message.caption or "")
            sent += 1
        except Exception as e:
            print(f"Error sending to {uid}: {e}")

    bot.send_message(message.chat.id, f"✅ Broadcast finished. Sent to {sent} users.")

# SUPPORTED PLATFORMS
def is_supported_url(url):
    platforms = ['tiktok.com', 'youtube.com', 'pinterest.com', 'pin.it', 'youtu.be',
                 'instagram.com', 'snapchat.com', 'facebook.com', 'x.com', 'twitter.com']
    return any(p in url.lower() for p in platforms)

def is_youtube_url(url):
    return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

# YOUTUBE LINK HANDLER
@bot.message_handler(func=lambda msg: is_youtube_url(msg.text))
def handle_youtube_url(msg):
    url = msg.text
    try:
        bot.send_chat_action(msg.chat.id, 'typing')
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            formats = info.get('formats', [])

        resolutions = {f'{f["height"]}p': f['format_id']
                       for f in formats if f.get('vcodec') != 'none' and f.get('height') <= 1080}

        if not resolutions:
            bot.send_message(msg.chat.id, "No suitable resolutions found.")
            return

        markup = InlineKeyboardMarkup(row_width=3)
        for res, fid in sorted(resolutions.items(), key=lambda x: int(x[0][:-1])):
            vid_id = str(uuid.uuid4())[:8]
            bot.video_info = getattr(bot, 'video_info', {})
            bot.video_info[vid_id] = {'url': url, 'format_id': fid}
            markup.add(InlineKeyboardButton(res, callback_data=f'dl:{vid_id}'))

        bot.send_message(msg.chat.id, f"Choose quality for: {title}", reply_markup=markup)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl:'))
def download_youtube_video(call):
    vid = call.data.split(":")[1]
    if not hasattr(bot, 'video_info') or vid not in bot.video_info:
        bot.answer_callback_query(call.id, "Download expired. Try again.")
        return

    data = bot.video_info[vid]
    url, fmt = data['url'], data['format_id']
    output_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")

    try:
        bot.answer_callback_query(call.id, "Downloading...")
        ydl_opts = {'format': fmt, 'outtmpl': output_path, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open(output_path, 'rb') as f:
            bot.send_video(call.message.chat.id, f, reply_to_message_id=call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error downloading: {e}")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

# SOCIAL VIDEO HANDLER
@bot.message_handler(func=lambda msg: is_supported_url(msg.text) and not is_youtube_url(msg.text))
def handle_social_video(msg):
    url = msg.text
    try:
        path = download_video_any(url)
        with open(path, 'rb') as f:
            bot.send_video(msg.chat.id, f)
    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

def download_video_any(url):
    filename = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
    ydl_opts = {
        'format': 'best',
        'outtmpl': filename,
        'quiet': True,
        'noplaylist': True,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return filename

# VIDEO UPLOAD
@bot.message_handler(content_types=['video'])
def handle_video_upload(msg):
    try:
        file_info = bot.get_file(msg.video.file_id)
        file_data = bot.download_file(file_info.file_path)
        path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
        with open(path, 'wb') as f:
            f.write(file_data)

        with open(path, 'rb') as f:
            bot.send_video(msg.chat.id, f)
    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

# START BOT
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
