import os
import json
import subprocess
import datetime
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import PromptSession
from utils import encode_base64
from llm import send_message

HISTORY_FILE = "chat_history.json"
PROMPT_FILE = "agent_manual.md"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_history(messages):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

def load_system_prompt():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Prompt file '{PROMPT_FILE}' not found. Continuing without a system prompt.")
        return None

def get_menu_choice(options, message):
    session = PromptSession()
    bindings = KeyBindings()
    
    choice = None

    @bindings.add('1')
    def _(event):
        nonlocal choice
        choice = 1
        event.app.exit()

    @bindings.add('2')
    def _(event):
        nonlocal choice
        choice = 2
        event.app.exit()

    @bindings.add('escape')
    @bindings.add('q')
    def _(event):
        nonlocal choice
        choice = None
        event.app.exit()

    menu_text = message + "\n" + "\n".join([f"{i}. {opt}" for i, opt in enumerate(options, 1)]) + "\nYour choice: "
    
    while choice is None:
        try:
            session.prompt(menu_text, key_bindings=bindings, multiline=False)
        except (EOFError, KeyboardInterrupt):
            choice = None
            break
    return choice

def chat_cli():
    messages = load_history()
    
    agent_manual_template = load_system_prompt()
    
    if agent_manual_template:
        current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
        agent_manual = agent_manual_template.replace("{{CURRENT_DATE}}", current_date)

        messages = [m for m in messages if m['role'] != 'system']
        messages.insert(0, {"role": "system", "content": agent_manual})

    print("Chat history loaded. Type '/exit' to quit.")
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
            save_history(messages)
            print("\nChat history saved. Goodbye!")
            break

        if user_input.strip().lower() == '/exit':
            save_history(messages)
            print("\nChat history saved. Goodbye!")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        # Initial call to get the LLM's plan
        response_message = send_message(messages, perform_search=False)

        # Check if the LLM wants to use a tool
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            # Add the assistant's decision to the history
            messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls
                ]
            })

            # Process tool calls
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                if function_name == "perform_web_search":
                    topic = arguments.get("topic")
                    print(f"LLM has decided to search for topics related to: \"{topic}\"")
                    # Add a dummy tool response to acknowledge
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Proceeding with web search for topic: {topic}"
                    })
                    # Make the second call with web search enabled
                    final_response_message = send_message(messages, perform_search=True)

                elif function_name == "execute_shell_command":
                    command = arguments.get("command")
                    tool_output = ""
                    if command:
                        print(f"\nLLM wants to execute the following command: `{command}`")
                        choice = get_menu_choice(["Allow", "Deny"], "Choose an action:")
                        if choice == 1:
                            try:
                                print(f"Executing: {command}")
                                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd(), check=False)
                                tool_output = f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
                            except Exception as e:
                                tool_output = f"Error executing command: {e}"
                        elif choice == 2:
                            tool_output = "User denied command execution."
                        else:
                            tool_output = "Command execution cancelled by user."
                    else:
                        tool_output = "LLM requested to execute an empty command."
                    
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_output})
                    # Make the second call to get the LLM's summary
                    final_response_message = send_message(messages, perform_search=False)
                else:
                    final_response_message = response_message # Unknown tool, do nothing

            response_message = final_response_message
        
        # Process and print the final response for the turn
        response_content = response_message.content

        if hasattr(response_message, 'annotations') and response_message.annotations:
            print("--- Sources ---")
            for i, annotation in enumerate(response_message.annotations, 1):
                if annotation.type == 'url_citation':
                    citation = annotation.url_citation
                    print(f"{i}. {citation.title}: {citation.url}")
            print("---------------\n")

        print("LLM:", response_content)

        # Add the final assistant message to history
        assistant_message = {"role": "assistant"}
        if response_content:
            assistant_message["content"] = response_content
        if hasattr(response_message, 'annotations') and response_message.annotations:
            assistant_message["annotations"] = [
                {
                    "type": ann.type,
                    "url_citation": {
                        "url": ann.url_citation.url,
                        "title": ann.url_citation.title,
                        "content": ann.url_citation.content,
                        "start_index": ann.url_citation.start_index,
                        "end_index": ann.url_citation.end_index
                    }
                } for ann in response_message.annotations if ann.type == 'url_citation'
            ]
        messages.append(assistant_message)