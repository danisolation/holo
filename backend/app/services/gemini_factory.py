"""Centralized Gemini client factory with proxy support.

All services should use `create_gemini_client()` instead of
`genai.Client(api_key=...)` directly. This ensures the optional
CF Worker proxy is applied consistently.
"""
from google import genai
from google.genai import types

from app.config import settings


def create_gemini_client(api_key: str | None = None) -> genai.Client:
    """Create a Gemini client, routing through proxy if configured."""
    key = api_key or settings.gemini_api_key
    http_options = None
    if settings.gemini_proxy_url:
        http_options = types.HttpOptions(base_url=settings.gemini_proxy_url)
    return genai.Client(api_key=key, http_options=http_options)
