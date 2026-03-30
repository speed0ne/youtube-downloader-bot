import logging
import os
import re

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.handlers import handle_message, handle_quality_callback

_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


class RedactFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return _TOKEN_RE.sub("bot***:***", msg)


_formatter = RedactFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(level=logging.INFO)
for handler in logging.root.handlers:
    handler.setFormatter(_formatter)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.environ["BOT_TOKEN"]

    # Use local Bot API server if configured, otherwise use default Telegram API
    local_api_url = os.environ.get("LOCAL_API_URL")

    builder = ApplicationBuilder().token(token)
    if local_api_url:
        builder = builder.base_url(
            local_api_url + "/bot"
        ).base_file_url(
            local_api_url + "/file/bot"
        )
        logger.info("Using local Bot API server at %s", local_api_url)

    app = builder.build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_quality_callback, pattern=r"^dl:"))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
