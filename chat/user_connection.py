from typing import List

from starlette.websockets import WebSocket

from chat.message import Message


class UserConnection:
    def __init__(self, user_id: str, username: str, websocket: WebSocket):
        self.user_id: str = user_id
        self.username: str = username
        self.websocket: WebSocket = websocket
        self.messages: List[Message] = []

    def accept(self):
        return self.websocket.accept()

    async def send_text(self, message: str):
        return await self.websocket.send_text(message)

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages(self):
        return self.messages
