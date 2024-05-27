from dataclasses import dataclass


@dataclass
class ChatRoomResponse:
    room_id: str
    room_name: str
    connection_count: int


@dataclass
class ListChatRoomsResponse:
    chat_rooms: list[ChatRoomResponse]
