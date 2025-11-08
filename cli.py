import os
import json
import subprocess
import datetime
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from llm import send_message
from session import ChatSession
from config import PROMPT_FILE

def load_system_prompt():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Prompt file '{PROMPT_FILE}' not found. Continuing without a system prompt.")
        return None

def get_menu_choice(options, message):
    # This function is no longer used in the reverted CLI, but kept for potential future use.
    pass

def handle_tool_calls(tool_calls, session):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        if function_name == "perform_web_search":
            topic = arguments.get("topic")
            print(f"LLM has decided to search for topics related to: \"{topic}\"")
            session.add_message("tool", f"Proceeding with web search for topic: {topic}", tool_call_id=tool_call.id)
            return send_message(session.messages, perform_search=True)

        elif function_name == "execute_shell_command":
            command = arguments.get("command")
            tool_output = ""
            if command:
                print(f"\nLLM wants to execute the following command: `{command}`")
                # Simplified approval for non-TUI interface
                approval = input("Allow? [y/n]: ").lower()
                if approval == 'y':
                    try:
                        print(f"Executing: {command}")
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd(), check=False)
                        tool_output = f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
                    except Exception as e:
                        tool_output = f"Error executing command: {e}"
                else:
                    tool_output = "User denied command execution."
            else:
                tool_output = "LLM requested to execute an empty command."
            
            session.add_message("tool", tool_output, tool_call_id=tool_call.id)
            return send_message(session.messages, perform_search=False)
    return None

def print_response(response_message):
    response_content = response_message.content

    if hasattr(response_message, 'annotations') and response_message.annotations:
        print("--- Sources ---")
        for i, annotation in enumerate(response_message.annotations, 1):
            if hasattr(annotation, 'type') and annotation.type == 'url_citation':
                citation = annotation.url_citation
                print(f"{i}. {citation.title}: {citation.url}")
        print("---------------\n")

    print("LLM:", response_content)

def chat_cli():
    session = ChatSession()
    
    agent_manual_template = load_system_prompt()
    
    if agent_manual_template:
        current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
        agent_manual = agent_manual_template.replace("{{CURRENT_DATE}}", current_date)
        session.set_system_prompt(agent_manual)

    print("New chat session started. Use '/chat save <name>', '/chat resume <name>', or '/chat new'.")
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
            print("\nGoodbye!")
            break

        if not user_input.strip():
            continue

        # Handle session commands
        parts = user_input.strip().split()
        if parts[0].lower() == '/chat':
            if len(parts) > 1:
                command = parts[1].lower()
                if command == 'save' and len(parts) > 2:
                    session.session_name = parts[2]
                    session.save()
                    continue
                elif command == 'resume' and len(parts) > 2:
                    session = ChatSession(session_name=parts[2])
                    session.load()
                    if agent_manual_template: # Re-apply system prompt
                        session.set_system_prompt(agent_manual)
                    continue
                elif command == 'new':
                    session = ChatSession()
                    if agent_manual_template: # Re-apply system prompt
                        session.set_system_prompt(agent_manual)
                    print("Started new chat session.")
                    continue
            print("Invalid command. Use: /chat save <name>, /chat resume <name>, or /chat new")
            continue

        session.add_message("user", user_input)

        response_message = send_message(session.messages, perform_search=False)

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            session.add_message("assistant", response_message.content or "", tool_calls=response_message.tool_calls)
            response_message = handle_tool_calls(response_message.tool_calls, session)
        
        if response_message:
            print_response(response_message)
            session.add_message("assistant", response_message.content, annotations=getattr(response_message, 'annotations', None))