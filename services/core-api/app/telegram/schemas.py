"""
TASKGENIUS Core API - Telegram Schemas

Pydantic models for Telegram webhook payloads and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    """Telegram user information from webhook."""

    id: int = Field(description="Telegram user ID")
    is_bot: bool = Field(default=False, description="Whether the user is a bot")
    first_name: str = Field(description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    username: Optional[str] = Field(default=None, description="User's username")


class TelegramMessage(BaseModel):
    """Telegram message from webhook."""

    message_id: int = Field(description="Message ID")
    from_user: TelegramUser = Field(alias="from", description="Message sender")
    chat: dict = Field(description="Chat information")
    date: int = Field(description="Message timestamp")
    text: Optional[str] = Field(default=None, description="Message text")


class TelegramUpdate(BaseModel):
    """Telegram webhook update payload."""

    update_id: int = Field(description="Update ID")
    message: Optional[TelegramMessage] = Field(default=None, description="Message if present")


class TelegramSendMessageRequest(BaseModel):
    """Request to send a message via Telegram Bot API."""

    chat_id: int = Field(description="Telegram chat ID")
    text: str = Field(description="Message text to send")
    parse_mode: Optional[str] = Field(default=None, description="Parse mode (HTML, Markdown, etc.)")


class TelegramSendMessageResponse(BaseModel):
    """Response from Telegram Bot API sendMessage."""

    ok: bool = Field(description="Whether the request was successful")
    result: Optional[dict] = Field(default=None, description="Result object if successful")


class TelegramLinkStartResponse(BaseModel):
    """Response when starting Telegram linking flow."""

    code: str = Field(description="Verification code to send to the Telegram bot")
    expires_in_seconds: int = Field(description="Validity window for the code in seconds")


class TelegramStatusResponse(BaseModel):
    """Current Telegram linking status for the authenticated user."""

    linked: bool = Field(description="Whether the user is linked to a Telegram account")
    telegram_username: Optional[str] = Field(
        default=None, description="Linked Telegram username if available"
    )
    notifications_enabled: bool = Field(
        description="Whether Telegram notifications are enabled for this user"
    )


class TelegramNotificationsToggleRequest(BaseModel):
    """Request body to enable/disable Telegram notifications."""

    enabled: bool = Field(description="Enable or disable Telegram notifications")


class TelegramUnlinkResponse(BaseModel):
    """Response after unlinking Telegram account."""

    unlinked: bool = Field(description="Whether unlinking succeeded")


class TelegramSummarySendResponse(BaseModel):
    """Response after sending weekly summary to Telegram."""

    sent: bool = Field(description="Whether the summary was sent successfully")
    message: Optional[str] = Field(default=None, description="Status message or error details")
