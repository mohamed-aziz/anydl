import enum
import tempfile
import boto3
from telegram import Bot, Update
import json
from telegram.ext import Dispatcher, Filters, MessageHandler
import subprocess
import re
import os

service = 'secretsmanager'
region = 'eu-west-3'
secret_name = 'prod/anydl'

client = boto3.client(service_name='secretsmanager', region_name=region)
response = client.get_secret_value(SecretId=secret_name)
telegram_key = json.loads(response['SecretString'])['TELEGRAM_KEY']

bot = Bot(token=telegram_key)
dispatcher = Dispatcher(bot, None, use_context=True)

    

class VideoTypes(enum.Enum):
    TIKTOK_VIDEO = 1
    YOUTUBE_VIDEO = 2
    INSTAGRAM_VIDEO = 3

def get_video_type(url):
    if "tiktok.com" in url:
        return VideoTypes.TIKTOK_VIDEO
    elif "youtube.com" in url or "youtu.be" in url:
        return VideoTypes.YOUTUBE_VIDEO
    elif "instagram.com" in url:
        return VideoTypes.INSTAGRAM_VIDEO

def download_tiktok(url):
    from TikTokApi import TikTokApi
    from TikTokApi.helpers import extract_video_id_from_url

    with TikTokApi() as api:
        video_id = extract_video_id_from_url(url)
        print("video_id: " + video_id)
        video = api.video(id=video_id)
        return video.bytes()

def generate_random_filename(length=10):
    import random
    import string
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def download_yt_dlp(url):
    from yt_dlp import YoutubeDL
    ydl_opts = {
        'outtmpl': f'/tmp/{generate_random_filename()}.%(ext)s',
    }

    ydl = YoutubeDL(ydl_opts)
    result = ydl.extract_info(url, download=True)
    if not result:
        print("No result")
        return

    video_path = result["requested_downloads"][0]["filepath"]
    with open(video_path, 'rb') as video_file:
        content = video_file.read()
    os.remove(video_path)
    return {
        "content": content,
        "title": result["fulltitle"],
        "url": url
    }


def fmt(ret, chunk_number: int, n_chunks: int):
    if n_chunks == 1:
        return f"{ret['title']}\n{ret['url']}"
    
    return f"{ret['title']} ({chunk_number + 1}/{n_chunks})\n{ret['url']}"

def split_video(input_file, output_pattern, chunk_size):
    """
    Splits a video file into smaller files of size less than the given chunk_size.
    """
    # Get the duration of the input video file
    duration = float(subprocess.check_output(['ffprobe', '-i', input_file, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0")]))
    
    # Calculate the number of chunks needed
    num_chunks = int(duration / chunk_size) + 1
    chunks = []
    # Split the video into chunks using ffmpeg
    for i in range(num_chunks):
        chunk_file = output_pattern.format(chunk_num=i)
        start_time = i * chunk_size
        subprocess.call(['ffmpeg', '-i', input_file, '-ss', str(start_time), '-t', str(chunk_size), '-c', 'copy', '-y', chunk_file])
        with open(chunk_file, 'rb') as chunk:
            chunks.append(chunk.read())        
        os.remove(chunk_file)
    
    return chunks


def split_video_if_larger_than_50mb(video: bytes):
    if len(video) < 50 * 1024 * 1024:
        return [video]
    
    with tempfile.NamedTemporaryFile() as f:
        f.write(video)
        f.flush()
        x = generate_random_filename(5)
        chunks = split_video(f.name, "/tmp/chunk" + x + "_{chunk_num}.mp4", 3 * 60)
        return chunks

def download(ctx, chat_id, url, dl_func):
    result = dl_func(url)
    assert result
    videos = split_video_if_larger_than_50mb(result["content"])
    n_chunks = len(videos)
    for chunk_number, video in enumerate(videos):
        ctx.bot.send_video(chat_id=chat_id, video=video, caption=fmt(result, chunk_number, n_chunks))


def dl(update, context):
    
    chat_id = update.message.chat_id
    chat_text = update.message.text
    
    # extract links from chat_message
    urls = re.findall(r'(https?://[^\s]+)', chat_text)
    assert urls
    assert len(urls) >= 1
    url = urls[0]
    video_type = get_video_type(url)
    if video_type == VideoTypes.TIKTOK_VIDEO:
        download(context, chat_id, url, download_yt_dlp)
    elif video_type == VideoTypes.YOUTUBE_VIDEO:
        download(context, chat_id, url, download_yt_dlp)
    elif video_type == VideoTypes.INSTAGRAM_VIDEO:
        download(context, chat_id, url, download_yt_dlp)

def lambda_handler(event, context):
    dispatcher.add_handler(MessageHandler(Filters.text, dl))
       
    try:
        dispatcher.process_update(
            Update.de_json(json.loads(event["body"]), bot)
        )

    except Exception as e:
        print(e)
        return {"statusCode": 500}

    return {
        "statusCode": 200
    }
