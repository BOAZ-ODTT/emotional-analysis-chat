import uuid
from typing import Dict

from chat.connection_manager import ConnectionManager
from chat.message import Message
from chat.user_connection import UserConnection


# TODO: ChatRoomRepository 또는 ChatRoomManager를 만들어서 관리하도록
class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.room_name = f"room {uuid.UUID(room_id).int % 10000}"
        self.manager = ConnectionManager()

    async def connect(self, connection: UserConnection):
        await self.manager.connect(connection)

    async def disconnect(self, connection: UserConnection):
        self.manager.disconnect(connection)

        if self.manager.count_connections() == 0:
            del chat_rooms[self.room_id]  # 사용자가 모두 나가면 방 삭제

    async def broadcast(self, message: Message):
        await self.manager.broadcast(message)

    async def broadcast_system_message(self, message: str):
        await self.manager.broadcast_system_message(message)

    def count_connections(self):
        return self.manager.count_connections()


chat_rooms: Dict[str, ChatRoom] = {}
