# resume/llm.py
"""
Central helper that returns (client_instance, model_name)
based on the admin-selected provider.

• Supports `gpt`  (OpenAI)   via openai-python ≥ 1.3
• Supports `deepseek`        via your DeepSeek wrapper
"""

from django.conf import settings
from openai import OpenAI
from .deepseek_client import client as deepseek_client  # already configured


def get_llm_client():
    """
    Decide which backend to use, return (client, model_name).

    Usage:
        llm_client, current_model = get_llm_client()
        llm_client.chat.completions.create(model=current_model, ...)
    """
    provider = getattr(settings, "LLM_PROVIDER", "gpt").lower()

    # ─── DeepSeek ────────────────────────────────────────────────────────
    if provider == "deepseek":
        return deepseek_client, settings.LLM_MODELS["deepseek"]

    # ─── Default → OpenAI GPT ────────────────────────────────────────────
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.LLM_TIMEOUT,
    )
    return client, settings.LLM_MODELS["gpt"]
