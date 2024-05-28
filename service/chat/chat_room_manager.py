import uuid
from typing import Dict, List, Optional

from service.chat.connection_manager import ConnectionManager
from service.chat.message import Message, MessageEventType, MessageType
from service.chat.user_connection import UserConnection


class NotFoundChatRoomException(Exception):
    def __init__(self, room_id):
        self.message = f"Chat room {room_id} not found"


class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.room_name = f"room {uuid.UUID(room_id).int % 10000}"
        self.manager = ConnectionManager()

    async def connect(self, connection: UserConnection):
        await self.manager.connect(connection)

    async def disconnect(self, connection: UserConnection):
        self.manager.disconnect(connection)

    async def broadcast(self, message: Message):
        await self.manager.broadcast(message)

    def count_connections(self):
        return self.manager.count_connections()

    def list_connections(self):
        return self.manager.get_connections()


class ChatRoomManager:
    def __init__(self):
        self.chat_room_by_id: Dict[str, ChatRoom] = {}

    def create_chat_room(self, room_id: str):
        chat_room = ChatRoom(room_id)
        self.chat_room_by_id[room_id] = chat_room
        return chat_room

    def get_chat_room(self, room_id: str) -> ChatRoom | None:
        return self.chat_room_by_id.get(room_id)

    def list_chat_rooms(self) -> List[ChatRoom]:
        return list(self.chat_room_by_id.values())

    def delete_chat_room(self, room_id: str):
        del self.chat_room_by_id[room_id]

    async def connect(self, room_id: str, connection: UserConnection):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            await chat_room.connect(connection)
            await self.broadcast_system_message(
                room_id=room_id,
                message=f'{connection.username}가 방에 입장했습니다.',
                event_type=MessageEventType.USER_JOINED,
            )
        else:
            raise NotFoundChatRoomException(room_id)

    async def disconnect(self, room_id: str, connection: UserConnection):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            await chat_room.disconnect(connection)
            await self.broadcast_system_message(
                room_id=room_id,
                message=f"{connection.username}가 방에서 나갔습니다.",
                event_type=MessageEventType.USER_LEFT,
            )

            if chat_room.count_connections() == 0:
                self.delete_chat_room(room_id)
        else:
            raise NotFoundChatRoomException(room_id)

    async def broadcast(self, room_id: str, message: Message):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            await chat_room.broadcast(message)
        else:
            raise NotFoundChatRoomException(room_id)

    async def broadcast_system_message(self, room_id: str, message: str, event_type: Optional[MessageEventType] = None):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            await chat_room.broadcast(
                Message(
                    username="System",
                    message=message,
                    message_type=MessageType.SYSTEM_MESSAGE,
                    event_type=event_type,
                )
            )
        else:
            raise NotFoundChatRoomException(room_id)

    def count_user_in_room(self, room_id: str):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            return chat_room.count_connections()
        else:
            raise NotFoundChatRoomException(room_id)

    def list_users_in_room(self, room_id: str):
        chat_room = self.get_chat_room(room_id)
        if chat_room:
            return chat_room.manager.get_connections()
        else:
            raise NotFoundChatRoomException(room_id)
