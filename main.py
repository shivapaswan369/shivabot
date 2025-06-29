"""Shiva's Multi-Channel YouTube ➜ Telegram Bot (Render version)
Usage:
    /add <YouTube-URL> [quality] [channel]
quality: 360p 480p 720p 1080p 2k 4k
"""
import os, logging, tempfile
from typing import List, Union
from telegram.ext import Updater, CommandHandler
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env var required")

ALLOWED_CHANNELS = []
for part in os.getenv("ALLOWED_CHANNELS", "").split(','):
    part = part.strip()
    if not part:
        continue
    if part.lstrip('-').isdigit():
        ALLOWED_CHANNELS.append(int(part))
    else:
        if not part.startswith('@'):
            part = '@' + part
        ALLOWED_CHANNELS.append(part)

MAX_FILESIZE = int(os.getenv("MAX_FILESIZE", "2000000000"))

QUALITY_MAP = {
    '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
    '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
    '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
    '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
    '2k': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
    '4k': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
}

def parse_channel(arg: str):
    if arg.lstrip('-').isdigit():
        cid = int(arg)
        return cid if cid in ALLOWED_CHANNELS else None
    if not arg.startswith('@'):
        arg = '@' + arg
    return arg if arg in ALLOWED_CHANNELS else None

def parse_quality(arg: str):
    k = arg.lower().rstrip('p')
    if k in QUALITY_MAP:
        return QUALITY_MAP[k]
    if k + 'p' in QUALITY_MAP:
        return QUALITY_MAP[k + 'p']
    return None

def add(update, context):
    if not context.args:
        update.message.reply_text("Usage: /add <YouTube-URL> [quality] [channel]")
        return
    url = context.args[0]
    quality_expr = None
    target = ALLOWED_CHANNELS[0] if ALLOWED_CHANNELS else update.message.chat_id
    for arg in context.args[1:]:
        q = parse_quality(arg)
        if q:
            quality_expr = q
            continue
        ch = parse_channel(arg)
        if ch is not None:
            target = ch
            continue
        update.message.reply_text(f"Unrecognised quality/channel arg: {arg}")
        return
    update.message.reply_text("⏬ Downloading…")
    ydl_opts = {
        'format': quality_expr or f"best[filesize<={MAX_FILESIZE}]/best",
        'outtmpl': os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        return
    title = info.get('title', 'Video')
    update.message.reply_text(f"📤 Uploading to {target} …")
    with open(file_path, 'rb') as vid:
        context.bot.send_video(chat_id=target, video=vid, caption=title)
    update.message.reply_text("✅ Done!")

def main():
    logging.basicConfig(level=logging.INFO)
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('add', add))
    updater.start_polling()
    logging.info("Bot started")
    updater.idle()

if __name__ == '__main__':
    main()
