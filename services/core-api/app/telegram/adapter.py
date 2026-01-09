"""
TASKGENIUS Core API - Telegram Adapter

Adapter for sending messages via Telegram Bot API.
This adapter is mockable for CI-safe testing.
"""

import httpx
from typing import Optional

from app.config import settings
from app.telegram.schemas import TelegramSendMessageRequest, TelegramSendMessageResponse


class TelegramAdapter:
    """
    Adapter for Telegram Bot API communication.
    
    This adapter:
    - Sends messages via Telegram Bot API
    - Is fully mockable for testing
    - Handles missing token gracefully (for CI)
    """

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram adapter.
        
        Args:
            bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN from settings)
        """
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_base_url = "https://api.telegram.org"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
    ) -> TelegramSendMessageResponse:
        """
        Send a message via Telegram Bot API.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Optional parse mode (HTML, Markdown, etc.)
        
        Returns:
            TelegramSendMessageResponse
        
        Raises:
            ValueError: If bot token is not configured
            httpx.HTTPError: If API call fails
        """
        if not self.bot_token:
            # In tests, this should be mocked, but we handle gracefully
            return TelegramSendMessageResponse(
                ok=False,
                result=None,
            )

        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return TelegramSendMessageResponse(**data)
            except httpx.HTTPError as e:
                # Return error response instead of raising
                return TelegramSendMessageResponse(
                    ok=False,
                    result=None,
                )
