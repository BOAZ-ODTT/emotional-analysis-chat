from collections import deque
from typing import List, Deque

from starlette.websockets import WebSocket

from config.config import MAX_MESSAGE_TO_SAVE
from service.chat.message import Message, MessageType


class UserConnection:
    def __init__(self, user_id: str, username: str, websocket: WebSocket):
        self.user_id: str = user_id
        self.username: str = username
        self.websocket: WebSocket = websocket
        self.messages: Deque[Message] = deque()

    async def accept(self):
        return await self.websocket.accept()

    async def close(self):
        return await self.websocket.close()

    async def send_message(self, message: Message):
        await self.websocket.send_text(message.json())
        if message.message_type == MessageType.USER_MESSAGE and message.user_id == self.user_id:
            self.save_user_message(message)

    def save_user_message(self, message: Message):
        self.messages.append(message)

        # 메모리 사용량을 줄이기 위해 지정된 메시지 수만 메모리에 저장
        if len(self.messages) > MAX_MESSAGE_TO_SAVE:
            self.messages.popleft()

    def list_messages(self) -> List[Message]:
        return list(self.messages)

    async def receive_message(self) -> Message:
        message = await self.websocket.receive_text()
        return Message.parse_raw(message)
