import logging
import httpx
from typing import Optional, List

from app.config import settings
from app.telegram.schemas import TelegramSendMessageRequest, TelegramSendMessageResponse

logger = logging.getLogger(__name__)


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

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """Delete webhook (for polling mode startup)."""
        if not self.bot_token:
            return False

        url = f"{self.api_base_url}/bot{self.bot_token}/deleteWebhook"
        params = {"drop_pending_updates": str(drop_pending_updates).lower()}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params, timeout=10.0)
                data = response.json()
                success = data.get("ok", False)
                if success:
                    logger.info("Telegram webhook deleted (drop_pending_updates=%s)", drop_pending_updates)
                return success
            except httpx.HTTPError as e:
                logger.error("Failed to delete webhook: %s", e)
                return False

    async def get_updates(self, offset: int = 0, timeout: int = 30) -> List[dict]:
        """Long-poll for updates (for polling mode)."""
        if not self.bot_token:
            return []

        url = f"{self.api_base_url}/bot{self.bot_token}/getUpdates"
        params = {"offset": offset, "timeout": timeout}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=timeout + 5)
                data = response.json()
                return data.get("result", []) if data.get("ok") else []
            except httpx.HTTPError as e:
                logger.error("Failed to get updates: %s", e)
                return []
