import json
import os

SESSIONS_DIR = "chats"

class ChatSession:
    def __init__(self, session_name="default"):
        self.session_name = session_name
        self.messages = []
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)

    @property
    def file_path(self):
        return os.path.join(SESSIONS_DIR, f"{self.session_name}.json")

    def load(self):
        if not os.path.exists(self.file_path):
            self.messages = []
            print(f"No session named '{self.session_name}' found. Starting a new one.")
            return False
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
            print(f"Resumed session: {self.session_name}")
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            self.messages = []
            return False

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)
        print(f"Session '{self.session_name}' saved.")

    def add_message(self, role, content, tool_calls=None, annotations=None, tool_call_id=None):
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        if annotations:
            serializable_annotations = []
            for ann in annotations:
                if hasattr(ann, 'type') and ann.type == 'url_citation':
                    citation = ann.url_citation
                    serializable_annotations.append({
                        "type": ann.type,
                        "url_citation": {
                            "url": citation.url,
                            "title": citation.title,
                            "content": citation.content,
                            "start_index": citation.start_index,
                            "end_index": citation.end_index
                        }
                    })
            message["annotations"] = serializable_annotations
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)

    def set_system_prompt(self, prompt):
        self.messages = [m for m in self.messages if m['role'] != 'system']
        self.messages.insert(0, {"role": "system", "content": prompt})

    def new_session(self):
        self.messages = []
