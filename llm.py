import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

PROPOSAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": "Executes a shell command in the current directory and returns the output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to execute."}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "perform_web_search",
            "description": "Signals the need to perform a web search by specifying the topic of information needed.",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string", "description": "A brief description of the topic or information needed to answer the user's question."}},
                "required": ["topic"],
            },
        },
    },
]

def send_message(messages, model="openai/gpt-4o", attachments=None, perform_search=False):
    extra_headers = {}
    body = {
        "model": model,
        "messages": messages,
    }
    extra_body = {}

    if perform_search:
        extra_body["plugins"] = [{"id": "web"}]
    else:
        body["tools"] = PROPOSAL_TOOLS

    if attachments:
        body["attachments"] = attachments

    completion = client.chat.completions.create(
        **body,
        extra_body=extra_body,
        extra_headers=extra_headers,
    )
    return completion.choices[0].message
