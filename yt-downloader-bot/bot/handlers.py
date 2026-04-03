import asyncio
import hashlib
import logging
import os
import re
import shutil
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.downloader import DownloadResult, download, download_audio, format_size, get_formats, get_stream_url

logger = logging.getLogger(__name__)

_raw = os.environ.get("ALLOWED_USERNAMES", "")
ALLOWED_USERNAMES: set[str] = {
    u.strip().lower().lstrip("@") for u in _raw.split(",") if u.strip()
}


def _is_user_allowed(update: Update) -> bool:
    if not ALLOWED_USERNAMES:
        return True
    user = update.effective_user
    if not user or not user.username:
        return False
    return user.username.lower() in ALLOWED_USERNAMES


YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages containing YouTube URLs."""
    if not _is_user_allowed(update):
        return

    text = update.message.text or ""
    match = YOUTUBE_REGEX.search(text)
    if not match:
        await update.message.reply_text(
            "Please send a valid YouTube link (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)."
        )
        return

    url = match.group(0)
    if not url.startswith("http"):
        url = "https://" + url

    status_msg = await update.message.reply_text("Fetching available qualities...")

    try:
        formats = get_formats(url)
    except Exception as e:
        logger.error("Failed to fetch formats: %s", e)
        await status_msg.edit_text(f"Error fetching video info: {e}")
        return

    url_id = _url_hash(url)

    # Clean up previous pending link for this user
    prev_url_id = context.user_data.get("pending_url_id")
    if prev_url_id and prev_url_id != url_id:
        context.bot_data.pop(f"url_{prev_url_id}", None)

    # Store URL in bot_data for callback retrieval
    context.bot_data[f"url_{url_id}"] = url
    context.user_data["pending_url_id"] = url_id

    buttons = []
    for fmt in formats:
        label = f"{fmt.resolution} - {format_size(fmt.filesize_approx)}"
        callback_data = f"dl:{url_id}:{fmt.height}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])

    # Add "Best quality" and "Audio only" options
    buttons.append(
        [InlineKeyboardButton("Best quality", callback_data=f"dl:{url_id}:best")]
    )
    buttons.append(
        [InlineKeyboardButton("Audio only (MP3)", callback_data=f"dl:{url_id}:audio")]
    )
    buttons.append(
        [InlineKeyboardButton("Stream only", callback_data=f"dl:{url_id}:stream")]
    )

    await status_msg.edit_text(
        "Choose format:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_quality_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quality selection from inline keyboard."""
    query = update.callback_query
    if not _is_user_allowed(update):
        await query.answer()
        return

    await query.answer()

    data = query.data
    if not data.startswith("dl:"):
        return

    _, url_id, height_str = data.split(":", 2)
    url = context.bot_data.get(f"url_{url_id}")
    if not url:
        await query.edit_message_text("Link expired. Please send the URL again.")
        return

    is_stream = height_str == "stream"
    is_audio = height_str == "audio"

    if is_stream:
        try:
            stream_url = get_stream_url(url)
            await query.edit_message_text(
                f"Stream link (expires in a few hours):\n\n{stream_url}"
            )
        except Exception as e:
            logger.error("Failed to get stream URL: %s", e)
            await query.edit_message_text(f"Error: {e}")
        finally:
            context.bot_data.pop(f"url_{url_id}", None)
        if context.user_data.get("pending_url_id") == url_id:
            context.user_data.pop("pending_url_id", None)
        return

    await query.edit_message_text("Downloading... 0%")

    loop = asyncio.get_event_loop()
    last_update = {"pct": 0, "time": 0.0}

    def progress_hook(d):
        if d["status"] != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if not total:
            return
        pct = int(d["downloaded_bytes"] / total * 100)
        rounded = pct // 10 * 10
        now = time.monotonic()
        if rounded > last_update["pct"] and now - last_update["time"] >= 2:
            last_update["pct"] = rounded
            last_update["time"] = now
            asyncio.run_coroutine_threadsafe(
                query.edit_message_text(f"Downloading... {rounded}%"),
                loop,
            )

    result: DownloadResult | None = None
    try:
        if is_audio:
            result = await loop.run_in_executor(
                None, lambda: download_audio(url, progress_hook=progress_hook)
            )
        else:
            height = int(height_str) if height_str != "best" else None
            result = await loop.run_in_executor(
                None, lambda: download(url, height, progress_hook=progress_hook)
            )

        filesize = os.path.getsize(result.filepath)
        await query.edit_message_text(
            f"Uploading ({format_size(filesize)})..."
        )

        if is_audio:
            with open(result.filepath, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_file,
                    title=result.title,
                    duration=result.duration,
                    read_timeout=300,
                    write_timeout=300,
                )
        else:
            with open(result.filepath, "rb") as video_file:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video_file,
                    duration=result.duration,
                    width=result.width,
                    height=result.height,
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300,
                )

        await query.edit_message_text("Done!")

    except Exception as e:
        logger.error("Download/upload failed: %s", e)
        await query.edit_message_text(f"Error: {e}")

    finally:
        if result:
            download_dir = os.path.dirname(result.filepath)
            shutil.rmtree(download_dir, ignore_errors=True)
        context.bot_data.pop(f"url_{url_id}", None)
        if context.user_data.get("pending_url_id") == url_id:
            context.user_data.pop("pending_url_id", None)
