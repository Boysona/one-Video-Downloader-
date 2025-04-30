
import shutil
import telebot
import yt_dlp
import os
import uuid
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from io import BytesIO

# === CONFIGURATION ===
BOT_TOKEN = "8136008912:AAHwM1ZBZ2WxgCnFpRA0MC_EIr9KcRQiF3c"
REQUIRED_CHANNEL = "@qolka_ka"  # Replace with your channel username
ADMIN_ID = 5978150981  # Replace with your actual Telegram user ID

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"
USERS_FILE = "users.txt"
existing_users = set()
admin_state = {}

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'r') as f:
        existing_users = set(line.strip() for line in f)

if os.path.exists(DOWNLOAD_DIR):
    shutil.rmtree(DOWNLOAD_DIR)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

BALOW_LINK = "https://www.tiktok.com/@zack3d2?_t=ZN-8vMGXY3EkEw&_r=1"

def get_balow_button():
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Summarize | Get", url=BALOW_LINK)
    keyboard.add(button)
    return keyboard

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def send_subscription_message(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        text="Join the Channel",
        url=f"https://t.me/{REQUIRED_CHANNEL[1:]}"
    ))
    bot.send_message(chat_id, "⚠️ Please join the channel to continue using this bot!", reply_markup=markup)

def is_supported_url(url):
    platforms = ['tiktok.com', 'youtube.com', 'pinterest.com', 'pin.it', 'youtu.be',
                 'instagram.com', 'snapchat.com', 'facebook.com', 'x.com', 'twitter.com']
    return any(p in url.lower() for p in platforms)

def is_youtube_url(url):
    return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.from_user.id)
    if user_id not in existing_users:
        existing_users.add(user_id)
        with open(USERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")

    if not check_subscription(message.from_user.id):
        return send_subscription_message(message.chat.id)

    if message.from_user.id == ADMIN_ID:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Send Broadcast", "Total Users", "/status")
        bot.send_message(message.chat.id, "Welcome Admin!", reply_markup=markup)
    else:
        first_name = message.from_user.first_name or "there"
        username = f"@{message.from_user.username}" if message.from_user.username else first_name
        text = f"👋 Salam {username}!\nSend me a link from supported platforms like TikTok, YouTube, Instagram, etc."
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['status'])
def status_handler(message):
    if message.from_user.id != ADMIN_ID:
        return
    total = len(existing_users)
    bot.send_message(message.chat.id, f"📊 Total Users: {total}")

@bot.message_handler(func=lambda m: m.text == "Total Users" and m.from_user.id == ADMIN_ID)
def total_users(message):
    bot.send_message(message.chat.id, f"Total users: {len(existing_users)}")

@bot.message_handler(func=lambda m: m.text == "Send Broadcast" and m.from_user.id == ADMIN_ID)
def send_broadcast(message):
    admin_state[message.from_user.id] = 'awaiting_broadcast'
    bot.send_message(message.chat.id, "Send the message to broadcast:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and admin_state.get(m.from_user.id) == 'awaiting_broadcast',
                     content_types=['text', 'photo', 'video', 'audio', 'document'])
def broadcast_message(message):
    admin_state[message.from_user.id] = None
    success = 0
    fail = 0
    for user_id in existing_users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
        except:
            fail += 1
    bot.send_message(message.chat.id, f"Broadcast done. Success: {success}, Fail: {fail}")

@bot.message_handler(func=lambda msg: is_youtube_url(msg.text))
def handle_youtube_url(msg):
    url = msg.text
    try:
        bot.send_chat_action(msg.chat.id, 'typing')
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            thumbnail_url = info_dict.get('thumbnail')
            title = info_dict.get('title', 'YouTube Video')
            formats = info_dict.get('formats', [])

        resolutions = {}
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('height') is not None:
                height = f['height']
                if height <= 1080:
                    resolutions[f'{height}p'] = f['format_id']

        if not resolutions:
            bot.send_message(msg.chat.id, "No video resolutions found.")
            return

        markup = InlineKeyboardMarkup(row_width=3)
        buttons = []
        sorted_resolutions = sorted(resolutions.keys(), key=lambda x: int(x[:-1]))
        for res in sorted_resolutions:
            format_id = resolutions[res]
            video_id = str(uuid.uuid4())[:8]
            bot.video_info = getattr(bot, 'video_info', {})
            bot.video_info[video_id] = {'url': url, 'format_id': format_id}
            buttons.append(InlineKeyboardButton(res, callback_data=f'dl:{video_id}'))
        markup.add(*buttons)

        if thumbnail_url:
            response = requests.get(thumbnail_url)
            image = Image.open(BytesIO(response.content))
            bio = BytesIO()
            image.save(bio, 'JPEG')
            bio.seek(0)
            bot.send_photo(msg.chat.id, photo=bio, caption=f"Choose quality: {title}", reply_markup=markup)
        else:
            bot.send_message(msg.chat.id, f"Choose quality: {title}", reply_markup=markup)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl:'))
def download_youtube_video(call):
    output_path = None
    try:
        video_id = call.data.split(':')[1]
        if not hasattr(bot, 'video_info') or video_id not in bot.video_info:
            bot.answer_callback_query(call.id, "Download expired.")
            return
        video_data = bot.video_info[video_id]
        url = video_data['url']
        format_id = video_data['format_id']
        output_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open(output_path, 'rb') as video_file:
            bot.send_video(call.message.chat.id, video_file, reply_to_message_id=call.message.message_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")
    finally:
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

@bot.message_handler(func=lambda msg: is_supported_url(msg.text) and not is_youtube_url(msg.text))
def handle_social_video(msg):
    url = msg.text
    video_path = None
    try:
        bot.send_chat_action(msg.chat.id, 'record_video')
        video_path = download_video_any(url)
        with open(video_path, 'rb') as video_file:
            bot.send_video(msg.chat.id, video_file)
    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

def download_video_any(url):
    unique_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.mp4")
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        'prefer_ffmpeg': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("Download failed")
        return output_path

if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling(timeout=20, long_polling_timeout=5)
