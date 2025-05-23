# # resume/deepseek_client.py
# from openai import OpenAI
# from django.conf import settings

# client = OpenAI(
#     api_key=settings.DEEPSEEK_API_KEY,
#     base_url=settings.LLM_CONFIG["BASE_URL"],
#     timeout=settings.LLM_CONFIG["TIMEOUT"],
# )
# resume/deepseek_client.py
from openai import OpenAI
from django.conf import settings

client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",  # Updated endpoint
    timeout=30  # Increased timeout
)