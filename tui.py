from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Log, Input, Static
from textual.containers import Grid
from textual import events
import time

class ConfirmScreen(Screen):
    def __init__(self, command: str):
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(f"LLM wants to execute: [b]{self.command}[/b]"),
            Static("\n1. Allow\n2. Deny\n3. Stop execution and give advice"),
            id="dialog",
        )

    def on_key(self, event: events.Key) -> None:
        with open("debug.log", "a") as f:
            f.write(f"[{time.time()}] Key pressed in ConfirmScreen: {event.key}\n")
        
        if event.key == "1":
            self.dismiss("allow")
        elif event.key == "2":
            self.dismiss("deny")
        elif event.key == "3":
            self.dismiss("advise")

class ChatApp(App):
    TITLE = "Agent"

    def __init__(self, chat_manager):
        super().__init__()
        self.chat_manager = chat_manager
        self.ctrl_c_count = 0
        self.ctrl_c_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Log(id="log")
        yield Input(placeholder="Enter your message...")

    def on_mount(self) -> None:
        self.chat_manager.app = self
        self.query_one("#log").write(self.chat_manager.get_history_text())
        self.query_one(Input).focus()

    def reset_ctrl_c(self):
        self.ctrl_c_count = 0

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.ctrl_c_count += 1
            if self.ctrl_c_count == 2:
                self.exit()
            else:
                self.query_one("#log").write("Press Ctrl+C again to exit.")
                if self.ctrl_c_timer:
                    self.ctrl_c_timer.stop()
                self.ctrl_c_timer = self.set_timer(2, self.reset_ctrl_c)
        else:
            self.ctrl_c_count = 0

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        await self.chat_manager.handle_input(user_input)
        event.input.value = ""

    def confirm_shell(self, command: str, callback) -> None:
        self.push_screen(ConfirmScreen(command), callback)
