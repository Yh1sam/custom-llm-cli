import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# -- Constants --
HISTORY_FILE = "chat_history.json"
PROMPT_FILE = "agent_manual.md"

# -- OpenAI Client --
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)
