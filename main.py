
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

# BOT TOKEN
bot = telebot.TeleBot("8136008912:AAHwM1ZBZ2WxgCnFpRA0MC_EIr9KcRQiF3c")

# Directory to store downloads
DOWNLOAD_DIR = "downloads"
if os.path.exists(DOWNLOAD_DIR):
    shutil.rmtree(DOWNLOAD_DIR)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# CTA button link
BALOW_LINK = "https://www.tiktok.com/@zack3d2?_t=ZN-8vMGXY3EkEw&_r=1"

def get_balow_button():
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Summarize | Get", url=BALOW_LINK)
    keyboard.add(button)
    return keyboard

def is_supported_url(url):
    platforms = ['tiktok.com', 'youtube.com', 'pinterest.com', 'pin.it', 'youtu.be',
                 'instagram.com', 'snapchat.com', 'facebook.com', 'x.com', 'twitter.com']
    return any(p in url.lower() for p in platforms)

def is_youtube_url(url):
    return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

@bot.message_handler(commands=['start'])
def start_handler(message):
    first_name = message.from_user.first_name or "there"
    username = f"@{message.from_user.username}" if message.from_user.username else first_name
    text = f"👋 Salam {username} sand me a link video TikTok, Facebook, Instagram, Pinterest, Snapchat, &more links from \nplatforms I’m downloading📥 it for you and will send it to you🚀 "
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['video'])
def handle_video_message(message):
    try:
        file_info = bot.get_file(message.video.file_id)
        unique_id = str(uuid.uuid4())
        file_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.mp4")
        downloaded_file = bot.download_file(file_info.file_path)

        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.send_chat_action(message.chat.id, 'upload_video')
        with open(file_path, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)

    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

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
            bot.send_message(msg.chat.id, "Ma jiro tayo muuqaal ah oo la heli karo.")
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
            try:
                response = requests.get(thumbnail_url)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                bio = BytesIO()
                image.save(bio, 'JPEG')
                bio.seek(0)
                bot.send_photo(msg.chat.id, photo=bio, caption=f"Dooro tayada aad rabto inaad soo dejiso: {title}", reply_markup=markup)
            except (requests.exceptions.RequestException, Exception) as e:
                bot.send_message(msg.chat.id, f"Dooro tayada aad rabto inaad soo dejiso: {title}", reply_markup=markup)
        else:
            bot.send_message(msg.chat.id, f"Dooro tayada aad rabto inaad soo dejiso: {title}", reply_markup=markup)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Error extracting YouTube info: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl:'))
def download_youtube_video(call):
    output_path = None
    try:
        video_id = call.data.split(':')[1]
        if not hasattr(bot, 'video_info') or video_id not in bot.video_info:
            bot.answer_callback_query(call.id, "Download expired. Please try again.")
            return
        video_data = bot.video_info[video_id]
        url = video_data['url']
        format_id = video_data['format_id']
        bot.answer_callback_query(call.id, f"Soo dejinta tayada {format_id}...")
        bot.send_chat_action(call.message.chat.id, 'record_video')
        output_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.send_chat_action(call.message.chat.id, 'upload_video')
        with open(output_path, 'rb') as video_file:
            bot.send_video(call.message.chat.id, video_file, reply_to_message_id=call.message.message_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error downloading video: {e}")
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

        bot.send_chat_action(msg.chat.id, 'upload_video')
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
        'format': 'best',  # Use best available format
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        'extract_flat': False,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'prefer_ffmpeg': True,
        'keepvideo': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise Exception("Failed to download video")
            return output_path
        except Exception as e:
            print(f"Error downloading video: {e}")
            raise

if __name__ == "__main__":
    try:
        print("Bot started...")
        bot.infinity_polling(timeout=20, long_polling_timeout=5)
    except Exception as e:
        print(f"Bot stopped: {e}")
