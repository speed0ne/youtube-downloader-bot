import hashlib
import logging
import os
import re
import shutil

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.downloader import DownloadResult, download, download_audio, format_size, get_formats

logger = logging.getLogger(__name__)

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages containing YouTube URLs."""
    text = update.message.text or ""
    match = YOUTUBE_REGEX.search(text)
    if not match:
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
    # Store URL in bot_data for callback retrieval
    context.bot_data[f"url_{url_id}"] = url

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

    await status_msg.edit_text(
        "Choose format:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_quality_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quality selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("dl:"):
        return

    _, url_id, height_str = data.split(":", 2)
    url = context.bot_data.get(f"url_{url_id}")
    if not url:
        await query.edit_message_text("Link expired. Please send the URL again.")
        return

    await query.edit_message_text("Downloading...")

    is_audio = height_str == "audio"

    result: DownloadResult | None = None
    try:
        if is_audio:
            result = download_audio(url)
        else:
            height = int(height_str) if height_str != "best" else None
            result = download(url, height)

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
