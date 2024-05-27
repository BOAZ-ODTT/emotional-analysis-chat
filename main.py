import asyncio
import random
import uuid
from typing import Dict

from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from chat.connection_manager import ConnectionManager
from chat.message import Message
from chat.user_connection import UserConnection
from dto.chat_room_response import ChatRoomResponse, ListChatRoomsResponse
from emotion_analysis.mock_emotion_classifier import MockEmotionClassifier

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

connection_manager = ConnectionManager()

# emotion_classifier = EmotionClassifier()


# m1 import 이슈로 작업할 때는 MockEmotionClassifier 사용
# main에 merge 되지 않도록 주의해주세요!
emotion_classifier = MockEmotionClassifier()


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


@app.post("/chat/rooms/new")
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
        connection_count=0,
    )


@app.websocket("/chat/{room_id}/connect/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    connection = UserConnection(
        user_id=str(uuid.uuid4()),
        websocket=websocket,
        username=username,
    )

    try:
        await chat_rooms[room_id].connect(connection)
        # 클라이언트에게 매개변수를 포함한 초기 메시지 전송
        await chat_rooms[room_id].broadcast(Message(
            username='Root', message=chat_rooms[room_id].room_name
        ))

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


@app.get("/chat/rooms")
async def get_rooms():
    return ListChatRoomsResponse(
        chat_rooms=[
            ChatRoomResponse(
                room_id=key,
                room_name=value.room_name,
                connection_count=value.count_connections(),
            ) for key, value in chat_rooms.items()
        ]
    )


# root
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='chat.html',
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


async def broadcast_emotion_message():
    while True:
        try:
            await asyncio.sleep(20)

            for key in chat_rooms.keys():
                manager = chat_rooms[key].manager

                connections = manager.get_connections()
                if not connections:
                    continue

                chose_connection: UserConnection = random.choice(connections)

                messages = chose_connection.get_messages()
                if len(messages) == 0:
                    await manager.broadcast_system_message(
                        message="메시지를 입력해보세요!"
                    )
                    continue

                # 임의로 최근 20개 메시지를 활용
                # 안정성을 위해 글자수 제한이 필요해보이지만 지금은 위험도가 낮은 걸로 판단되어 제한하지 않음
                target_messages = messages[-20:]
                combined_message = "\n".join([message.message for message in target_messages])

                emotion_text = emotion_classifier.classify(combined_message)

                await manager.broadcast_system_message(
                    message=f"{chose_connection.username}의 {emotion_text} 느껴집니다."
                )

        except Exception as e:
            print(e)


@app.on_event("startup")
def startup_event():
    asyncio.create_task(broadcast_emotion_message())
