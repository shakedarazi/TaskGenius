"""
TASKGENIUS Chatbot Service - LLM Repository

Encapsulates OpenAI client and raw API calls. The service layer must not
import the OpenAI SDK directly.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> Optional[AsyncOpenAI]:
    """Get or create OpenAI client (singleton)."""
    global _client
    if _client is None and settings.USE_LLM and settings.OPENAI_API_KEY:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


class LLMRepositoryInterface(ABC):
    """Abstract interface for LLM backend."""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 500,
        timeout: float = 10.0,
    ) -> Optional[str]:
        """Call LLM and return raw content, or None on failure."""
        pass


class OpenAIRepository(LLMRepositoryInterface):
    """OpenAI implementation of LLM repository."""

    async def generate_completion(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 500,
        timeout: float = 10.0,
    ) -> Optional[str]:
        """Call OpenAI chat completions API."""
        client = _get_client()
        if not client:
            return None
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content if response.choices else None
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")
            return None


def get_llm_repository() -> LLMRepositoryInterface:
    """Get LLM repository instance."""
    return OpenAIRepository()
