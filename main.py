import os
import logging
import tempfile
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ── Render के फ़्री Web-Service पर port-scan टालने के लिए ──
os.environ["PORT"] = "10000"

# ── ENV VARIABLES ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN env-var missing!")

ALLOWED_CHANNELS = os.getenv("ALLOWED_CHANNELS", "").split(",")
MAX_SIZE_MB = 1900  # 1.9 GB (Telegram hard-limit≈2 GB)

QUALITY_MAP = {
    "360p": 360,
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
    "2k": 1440,
    "4k": 2160,
}

# ── LOGGING ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("ShivaBot")

# ── HELPERS ────────────────────────────────────────────────
def build_yt_command(url: str, height: int) -> str:
    fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
    return (
        f'yt-dlp --geo-bypass --geo-bypass-country US '
        f'--cookies cookies.txt -f "{fmt}" '
        f'-o "%(title)s.%(ext)s" "{url}"'
    )

def channel_allowed(chat_id: int | str) -> bool:
    return not ALLOWED_CHANNELS or str(chat_id) in ALLOWED_CHANNELS

# ── BOT COMMANDS ───────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Use /add <YouTube-URL> <quality>\n"
        "Example: /add https://youtu.be/dQw4w9WgXcQ 480p"
    )

async def add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not channel_allowed(chat_id):
        await update.message.reply_text("⛔ You’re not allowed to use this bot.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text("⚠️ Usage: /add <url> <quality>")
        return

    url, quality_arg = ctx.args[0], ctx.args[1].lower()
    height = QUALITY_MAP.get(quality_arg.rstrip("p"))
    if not height:
        await update.message.reply_text("❌ Unsupported quality.")
        return

    await update.message.reply_text("📥 Downloading…")
    cmd = build_yt_command(url, height)
    log.info("Running: %s", cmd)
    code = os.system(cmd)

    # find downloaded file
    video_path = None
    for f in os.listdir("."):
        if f.endswith((".mp4", ".mkv", ".webm")):
            video_path = f
            break

    if code != 0 or not video_path:
        await update.message.reply_text("❌ Download failed or blocked.")
        return

    # size check
    if os.path.getsize(video_path) > MAX_SIZE_MB * 1024 * 1024:
        await update.message.reply_text("❌ File too big for Telegram.")
        os.remove(video_path)
        return

    await update.message.reply_text("📤 Uploading…")
    try:
        with open(video_path, "rb") as vid:
            await ctx.bot.send_video(chat_id=chat_id, video=vid)
        await update.message.reply_text("✅ Done!")
    except Exception as e:
        await update.message.reply_text(f"❌ Upload error: {e}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

# ── MAIN ───────────────────────────────────────────────────
def main():
    log.info("Allowed channels: %s", ALLOWED_CHANNELS or "ALL")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    log.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()

