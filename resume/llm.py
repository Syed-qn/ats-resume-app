from django.conf import settings
from openai import OpenAI
from .deepseek_client import client as deepseek_client # already configured

def get_llm_client():
    """
    Returns a tuple of (client_instance, model_name) according to
    settings.LLM_PROVIDER so the rest of the code doesn’t care which
    backend is active.
    """
    provider = getattr(settings, "LLM_PROVIDER", "gpt").lower()

     if provider == 'deepseek':
        # DeepSeek SDK is OpenAI-compatible – reuse as-is
        return deepseek_client, settings.LLM_MODELS['deepseek']

    # Default → OpenAI
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.LLM_TIMEOUT,
    )
    return client, settings.LLM_MODELS['gpt']
