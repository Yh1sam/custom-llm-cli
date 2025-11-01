import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

def encode_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

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

def chat_cli():
    messages = []
    print("Type '/exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.strip() == '/exit':
            break
        if user_input.startswith('/pdf '):
            pdf_path = user_input[5:].strip()
            if not os.path.exists(pdf_path):
                print("PDF file not found.")
                continue
            prompt = input("請輸入對此PDF的分析指令：")
            messages.append({"role": "user", "content": prompt})
            pdf_b64 = encode_base64(pdf_path)
            attachments = [{"type": "application/pdf", "data": pdf_b64}]
            response = send_message(messages, attachments=attachments)
            print("LLM:", response)
            messages.append({"role": "assistant", "content": response})
        elif user_input.startswith('/img '):
            img_path = user_input[5:].strip()
            if not os.path.exists(img_path):
                print("Image file not found.")
                continue
            prompt = input("請輸入對此圖片的問題或指令：")
            messages.append({"role": "user", "content": prompt})
            img_b64 = encode_base64(img_path)
            attachments = [{"type": "image/png", "data": img_b64}]
            response = send_message(messages, attachments=attachments)
            print("LLM:", response)
            messages.append({"role": "assistant", "content": response})
        else:
            messages.append({"role": "user", "content": user_input})
            response = send_message(messages)
            print("LLM:", response)
            messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    chat_cli()
