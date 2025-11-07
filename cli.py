import os
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from utils import encode_base64
from llm import send_message

def chat_cli():
    messages = []
    print("Press Alt+Enter for a new line. Press Enter to send. Press Ctrl+C or Ctrl+D to exit.")

    bindings = KeyBindings()

    @bindings.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')

    @bindings.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()

    while True:
        try:
            user_input = prompt("You: ", multiline=True, key_bindings=bindings)
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.startswith('/pdf '):
            pdf_path = user_input[5:].strip()
            if not os.path.exists(pdf_path):
                print("PDF file not found.")
                continue
            prompt_text = prompt("Enter your prompt for the PDF: ", multiline=True, key_bindings=bindings)
            messages.append({"role": "user", "content": prompt_text})
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
            prompt_text = prompt("Enter your prompt for the image: ", multiline=True, key_bindings=bindings)
            messages.append({"role": "user", "content": prompt_text})
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
