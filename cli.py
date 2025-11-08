import os
import json
import subprocess
import datetime
from llm import send_message
from session import ChatSession
from config import PROMPT_FILE
from tui import ChatApp

def load_system_prompt():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Prompt file '{PROMPT_FILE}' not found. Continuing without a system prompt.")
        return None

class ChatManager:
    def __init__(self):
        self.session = ChatSession()
        self.agent_manual_template = load_system_prompt()
        self.app = None
        self.apply_system_prompt()
        self._tool_call_context = None

    def apply_system_prompt(self):
        if self.agent_manual_template:
            current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
            agent_manual = self.agent_manual_template.replace("{{CURRENT_DATE}}", current_date)
            self.session.set_system_prompt(agent_manual)

    def get_history_text(self):
        messages_to_render = [m for m in self.session.messages if m['role'] != 'system']
        formatted_messages = []
        for m in messages_to_render:
            role = m['role']
            if role == 'user':
                role = 'You'
            elif role == 'assistant':
                role = 'LLM'
            formatted_messages.append(f"{role.capitalize()}: {m['content']}")
        return "\n".join(formatted_messages)

    async def handle_input(self, user_input):
        if not user_input.strip():
            self.update_log()
            return

        parts = user_input.strip().split()
        if parts[0].lower() == '/chat':
            self.handle_chat_command(parts)
            self.update_log()
            return

        self.session.add_message("user", user_input)
        self.update_log()
        
        response_message = send_message(self.session.messages, perform_search=False)

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            self.session.add_message("assistant", response_message.content or "", tool_calls=response_message.tool_calls)
            self.handle_tool_calls(response_message.tool_calls)
        else:
            if response_message:
                self.session.add_message("assistant", response_message.content, annotations=getattr(response_message, 'annotations', None))
        
        self.update_log()

    def _process_shell_confirmation(self, choice: str):
        tool_call = self._tool_call_context
        if not tool_call:
            return

        command = json.loads(tool_call.function.arguments).get("command")
        tool_output = ""

        if choice == "allow":
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd(), check=False)
                tool_output = f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
            except Exception as e:
                tool_output = f"Error executing command: {e}"
        elif choice == "deny":
            tool_output = "User denied command execution."
        elif choice == "advise":
            tool_output = "User has stopped the execution and requested advice on the command."
        else:
            tool_output = "User cancelled the operation."
        
        self.session.add_message("tool", tool_output, tool_call_id=tool_call.id)
        
        # Make the final call to the LLM
        final_response = send_message(self.session.messages, perform_search=False)
        if final_response:
            self.session.add_message("assistant", final_response.content, annotations=getattr(final_response, 'annotations', None))
        
        self._tool_call_context = None
        self.update_log()

    def handle_tool_calls(self, tool_calls):
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if function_name == "perform_web_search":
                topic = arguments.get("topic")
                self.session.add_message("tool", f"Proceeding with web search for topic: {topic}", tool_call_id=tool_call.id)
                response = send_message(self.session.messages, perform_search=True)
                if response:
                    self.session.add_message("assistant", response.content, annotations=getattr(response, 'annotations', None))
                self.update_log()

            elif function_name == "execute_shell_command":
                self._tool_call_context = tool_call
                command = arguments.get("command")
                self.app.confirm_shell(command, self._process_shell_confirmation)

    def handle_chat_command(self, parts):
        if len(parts) > 1:
            command = parts[1].lower()
            if command == 'save' and len(parts) > 2:
                self.session.session_name = parts[2]
                self.session.save()
            elif command == 'resume' and len(parts) > 2:
                self.session = ChatSession(session_name=parts[2])
                self.session.load()
                self.apply_system_prompt()
            elif command == 'new':
                self.session = ChatSession()
                self.apply_system_prompt()

    def update_log(self):
        log_widget = self.app.query_one("#log")
        log_widget.clear()
        log_widget.write(self.get_history_text())

def chat_cli():
    chat_manager = ChatManager()
    app = ChatApp(chat_manager)
    app.run()