from typing import List

from starlette.websockets import WebSocket

from config.config import MAX_MESSAGE_TO_SAVE
from service.chat.message import Message


class UserConnection:
    def __init__(self, user_id: str, username: str, websocket: WebSocket):
        self.user_id: str = user_id
        self.username: str = username
        self.websocket: WebSocket = websocket
        self.messages: List[Message] = []

    async def accept(self):
        return await self.websocket.accept()

    async def close(self):
        return await self.websocket.close()

    async def send_message(self, message: Message):
        await self.websocket.send_text(message.json())
        self.save_message(message)

    def save_message(self, message: Message):
        self.messages.append(message)
        # 메모리 사용량을 줄이기 위해 지정된 메시지 수만 메모리에 저장
        if len(self.messages) > MAX_MESSAGE_TO_SAVE:
            self.messages.pop(0)

    def list_messages(self) -> List[Message]:
        return self.messages

    async def receive_message(self) -> Message:
        message = await self.websocket.receive_text()
        return Message.parse_raw(message)
