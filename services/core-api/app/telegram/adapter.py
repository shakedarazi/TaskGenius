import logging
import httpx
from typing import Optional

from app.config import settings
from app.telegram.schemas import TelegramSendMessageRequest, TelegramSendMessageResponse


class TelegramAdapter:

    def __init__(self, bot_token: Optional[str] = None):

        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_base_url = "https://api.telegram.org"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
    ) -> TelegramSendMessageResponse:

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
