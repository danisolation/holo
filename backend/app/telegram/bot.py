"""Telegram bot lifecycle management.

Uses python-telegram-bot v22.7 async Application with long-polling.
Integrated into FastAPI lifespan — starts polling in background, stops on shutdown.
Per CONTEXT.md: long-polling (not webhook) for personal use simplicity.
"""
import asyncio

from loguru import logger
from telegram import Bot
from telegram.ext import Application

from app.config import settings


class TelegramBot:
    """Manages Telegram bot lifecycle and provides message sending utility."""

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.app: Application | None = None
        self._polling_task: asyncio.Task | None = None

    @property
    def is_configured(self) -> bool:
        """Check if bot token and chat_id are set."""
        return bool(self.token) and bool(self.chat_id)

    async def start(self):
        """Initialize bot application and start long-polling in background.

        Call this from FastAPI lifespan startup.
        Skips silently if token/chat_id not configured (same pattern as gemini_api_key).
        """
        if not self.is_configured:
            logger.warning(
                "Telegram bot not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID empty). "
                "Bot features disabled."
            )
            return

        from app.telegram.handlers import register_handlers

        self.app = Application.builder().token(self.token).build()
        register_handlers(self.app)

        # Initialize the application (sets up bot info, handlers)
        await self.app.initialize()
        await self.app.start()

        # Start polling in background task — non-blocking
        self._polling_task = asyncio.create_task(
            self.app.updater.start_polling(drop_pending_updates=True)
        )
        logger.info("Telegram bot started with long-polling")

    async def stop(self):
        """Stop polling and shut down bot application.

        Call this from FastAPI lifespan shutdown.
        """
        if self.app is None:
            return

        try:
            if self.app.updater and self.app.updater.running:
                await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    async def send_message(self, text: str, chat_id: str | None = None) -> bool:
        """Send an HTML-formatted message to a Telegram chat.

        Retries 2x on failure per CONTEXT.md D-3.4. Never raises — returns
        False on failure so alert/pipeline code isn't blocked.

        Args:
            text: HTML-formatted message text
            chat_id: Target chat ID. Defaults to settings.telegram_chat_id.

        Returns: True if sent successfully, False otherwise.
        """
        target = chat_id or self.chat_id
        if not self.is_configured or not target:
            logger.warning("Cannot send message: bot not configured")
            return False

        bot = Bot(token=self.token)
        max_retries = 2

        for attempt in range(1, max_retries + 1):
            try:
                await bot.send_message(
                    chat_id=target,
                    text=text,
                    parse_mode="HTML",
                )
                return True
            except Exception as e:
                logger.warning(
                    f"Telegram send failed (attempt {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 * attempt)  # Simple backoff: 2s, 4s

        logger.error(f"Failed to send Telegram message after {max_retries} attempts")
        return False


# Singleton instance — shared across the application
telegram_bot = TelegramBot()
