import asyncio
import uuid

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from service.chat.chat_room_manager import chat_rooms, ChatRoom
from service.chat.message import Message
from service.chat.user_connection import UserConnection
from dto.chat_room_response import ChatRoomResponse, ListChatRoomsResponse

router = APIRouter(prefix="/v1/chat")


@router.post("/rooms/new")
async def create_chat_room():
    new_room_id = str(uuid.uuid4())
    chat_rooms[new_room_id] = ChatRoom(new_room_id)

    # 채팅방 클렌징을 위해 일정 시간동안 입장한 사람이 없다면 채팅방 제거
    async def check_and_clear_inactive_room(room_id):
        await asyncio.sleep(10)
        if room_id in chat_rooms and chat_rooms[room_id].count_connections() == 0:
            del chat_rooms[room_id]

    asyncio.create_task(check_and_clear_inactive_room(new_room_id))

    return ChatRoomResponse(
        room_id=new_room_id,
        room_name=chat_rooms[new_room_id].room_name,
        user_count=0,
    )


@router.get("/rooms")
async def get_rooms():
    return ListChatRoomsResponse(
        chat_rooms=[
            ChatRoomResponse(
                room_id=key,
                room_name=value.room_name,
                user_count=value.count_connections(),
            ) for key, value in chat_rooms.items()
        ]
    )


@router.websocket("/{room_id}/connect/{username}")
async def connect_chat_room(websocket: WebSocket, room_id: str, username: str):
    connection = UserConnection(
        user_id=str(uuid.uuid4()),
        websocket=websocket,
        username=username,
    )

    try:
        await chat_rooms[room_id].connect(connection)
        await chat_rooms[room_id].broadcast_system_message(message=f'{username}가 방에 입장했습니다.')

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await chat_rooms[room_id].broadcast(message)
            connection.add_message(message)

    except WebSocketDisconnect:
        await chat_rooms[room_id].disconnect(connection)
        if room_id in chat_rooms:
            await chat_rooms[room_id].broadcast(Message(username="System", message=f"{username}가 방에서 나갔습니다."))
