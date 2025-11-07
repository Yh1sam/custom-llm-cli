import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

def send_message(messages, model="openai/gpt-4o", attachments=None):
    extra_headers = {}
    body = {
        "model": model,
        "messages": messages,
    }
    if attachments:
        body["attachments"] = attachments

    completion = client.chat.completions.create(
        **body,
        extra_headers=extra_headers,
    )
    return completion.choices[0].message.content
