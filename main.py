"""
ShivaTube ➜ Telegram Bot
---------------------------------
Commands:
    /add <YouTube-URL> [quality] [channel]
        quality  : 360p 480p 720p 1080p 2k 4k  (default best≤2 GB)
        channel  : -100123…  या  @username  (optional)

Env-Vars required on Render (or any host):
    BOT_TOKEN         = Telegram bot token  ("12345:ABC…")
    ALLOWED_CHANNELS  = comma-separated list → -1002566377076,@mychannel
    MAX_FILESIZE      = (optional) bytes limit, default 2 GB
"""

import os, logging, tempfile
from telegram.ext import Updater, CommandHandler
from yt_dlp import YoutubeDL

# ───────────────────────────────────────────────────────────
# 1️⃣  CONFIG
# ───────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env-var missing!")

ALLOWED = []
for part in os.getenv("ALLOWED_CHANNELS", "").split(","):
    part = part.strip()
    if not part:
        continue
    if part.lstrip("-").isdigit():
        ALLOWED.append(int(part))
    else:
        if not part.startswith("@"):
            part = "@" + part
        ALLOWED.append(part)

MAX_SIZE = int(os.getenv("MAX_FILESIZE", "2000000000"))  # 2 GB default

QUALITY_FMT = {
    "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "2k":    "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "4k":    "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ───────────────────────────────────────────────────────────
# 2️⃣  HELPERS
# ───────────────────────────────────────────────────────────
def pick_channel(arg: str):
    if arg.lstrip("-").isdigit():
        cid = int(arg)
        return cid if cid in ALLOWED else None
    if not arg.startswith("@"):
        arg = "@" + arg
    return arg if arg in ALLOWED else None


def pick_quality(arg: str):
    key = arg.lower().rstrip("p")
    if key in QUALITY_FMT:
        return QUALITY_FMT[key]
    if key + "p" in QUALITY_FMT:
        return QUALITY_FMT[key + "p"]
    return None


# ───────────────────────────────────────────────────────────
# 3️⃣  /add  COMMAND
# ───────────────────────────────────────────────────────────
def add(update, ctx):
    if not ctx.args:
        update.message.reply_text("Usage: /add <YouTube-URL> [quality] [channel]")
        return

    url = ctx.args[0]
    q_expr = None
    target = ALLOWED[0] if ALLOWED else update.effective_chat.id

    # बाकी arguments से quality / channel निकालो
    for arg in ctx.args[1:]:
        q = pick_quality(arg)
        if q:
            q_expr = q
            continue
        ch = pick_channel(arg)
        if ch is not None:
            target = ch
            continue
        update.message.reply_text(f"Unrecognised arg: {arg}")
        return

    update.message.reply_text("⏬ Downloading…")

    ydl_opts = {
        "format": q_expr or f"best[filesize<={MAX_SIZE}]/best",
        "outtmpl": os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
        "quiet": True,
        # geo-unlock
        "geo_bypass": True,
        "geo_bypass_country": "US",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        return

    title = info.get("title", "Video")
    update.message.reply_text(f"📤 Uploading to {target} …")
    with open(file_path, "rb") as vid:
        ctx.bot.send_video(chat_id=target, video=vid, caption=title)
    update.message.reply_text("✅ Done!")


# ───────────────────────────────────────────────────────────
# 4️⃣  MAIN
# ───────────────────────────────────────────────────────────
def main():
    logging.info("Allowed channels: %s", ALLOWED or "ALL (no env set)")
    up = Updater(BOT_TOKEN, use_context=True)
    up.dispatcher.add_handler(CommandHandler("add", add))
    up.start_polling()
    logging.info("Bot started")
    up.idle()


if __name__ == "__main__":
    main()
