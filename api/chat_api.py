import asyncio
import uuid

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from core.dependencies import chat_room_manager
from dto.chat_room_response import ChatRoomResponse, ListChatRoomsResponse
from service.chat.chat_room_manager import NotFoundChatRoomException
from service.chat.user_connection import UserConnection

router = APIRouter(prefix="/v1/chat")


@router.post("/rooms/new")
async def create_chat_room():
    new_room_id = str(uuid.uuid4())
    chat_room = chat_room_manager.create_chat_room(room_id=new_room_id)

    # 채팅방 클렌징을 위해 일정 시간동안 입장한 사람이 없다면 채팅방 제거
    async def check_and_clear_inactive_room(room_id):
        await asyncio.sleep(10)
        try:
            if chat_room_manager.count_user_in_room(room_id=room_id) == 0:
                chat_room_manager.delete_chat_room(room_id=room_id)
        except NotFoundChatRoomException:
            pass
        except Exception as e:
            print(e)


    asyncio.create_task(check_and_clear_inactive_room(new_room_id))

    return ChatRoomResponse(
        room_id=new_room_id,
        room_name=chat_room.room_name,
        user_count=0,
    )


@router.get("/rooms")
async def list_rooms():
    return ListChatRoomsResponse(
        chat_rooms=[
            ChatRoomResponse(
                room_id=room.room_id,
                room_name=room.room_name,
                user_count=room.count_connections(),
            ) for room in chat_room_manager.list_chat_rooms()
        ]
    )


@router.get("/rooms/{room_id}")
async def get_room(room_id: str):
    room = chat_room_manager.get_chat_room(room_id=room_id)

    if room is None:
        return {"message": f"Chat room {room_id} not found"}, 404

    return ChatRoomResponse(
        room_id=room.room_id,
        room_name=room.room_name,
        user_count=room.count_connections(),
    )




@router.websocket("/{room_id}/connect/{username}")
async def connect_chat_room(websocket: WebSocket, room_id: str, username: str):
    connection = UserConnection(
        user_id=str(uuid.uuid4()),
        websocket=websocket,
        username=username,
    )

    try:
        await chat_room_manager.connect(room_id=room_id, connection=connection)

        while True:
            message = await connection.receive_message()
            await chat_room_manager.broadcast(room_id=room_id, message=message)

    except WebSocketDisconnect:
        await chat_room_manager.disconnect(room_id=room_id, connection=connection)
