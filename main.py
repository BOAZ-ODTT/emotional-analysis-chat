import asyncio
import random
import uuid
from typing import Set, Dict

from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from emotion_classifier import EmotionClassifier
from message import Message
from mock_emotion_classifier import MockEmotionClassifier
from user_connection import UserConnection

app = FastAPI()
templates = Jinja2Templates(directory="templates")

connection_manager = ConnectionManager()

# emotion_classifier = EmotionClassifier()
# m1 import 이슈로 작업할 때는 MockEmotionClassifier 사용
emotion_classifier = MockEmotionClassifier()


class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.manager = ConnectionManager()
        self.users: Set[UserConnection] = set()  # 사용자 수 추적

    async def connect(self, connection: UserConnection):
        await self.manager.connect(connection)
        self.users.add(connection)  # 사용자 추가

    async def disconnect(self, connection: UserConnection):
        self.manager.disconnect(connection)
        self.users.remove(connection)  # 사용자 제거
        if not self.users:
            del chat_rooms[self.room_id]  # 사용자가 모두 나가면 방 삭제

    async def broadcast(self, message: Message):
        await self.manager.broadcast(message)


chat_rooms: Dict[str, ChatRoom] = {}


@app.websocket("/chat/connect/new/{username}")
async def create_new_chat_room(websocket: WebSocket, username: str):
    room_id = str(uuid.uuid4())  # 무작위로 UUID 생성
    chat_rooms[room_id] = ChatRoom(room_id)

    print(chat_rooms)

    connection = UserConnection(
        user_id=str(uuid.uuid4()),
        websocket=websocket,
        username=username,
    )

    await chat_rooms[room_id].connect(connection)

    try:
        await chat_rooms[room_id].broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await chat_rooms[room_id].broadcast(message)
            connection.add_message(message)

    except WebSocketDisconnect:
        await chat_rooms[room_id].disconnect(connection)
        if room_id in chat_rooms:
            await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


@app.websocket("/chat/{room_id}/connect/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    connection = UserConnection(
        user_id=str(uuid.uuid4()),
        websocket=websocket,
        username=username,
    )

    await chat_rooms[room_id].connect(connection)

    try:
        await chat_rooms[room_id].broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await chat_rooms[room_id].broadcast(message)
            connection.add_message(message)

    except WebSocketDisconnect:
        await chat_rooms[room_id].disconnect(connection)
        if room_id in chat_rooms:
            await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


@app.get("/chat/rooms")
async def get_rooms():
    return list(chat_rooms.keys())


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
                    await manager.broadcast(
                        Message(
                            username="System",
                            message=f"메시지를 입력해보세요!",
                        )
                    )
                    continue
                last_message = messages[-1].message

                emotion_text = emotion_classifier.classify(last_message)

                await manager.broadcast(
                    Message(
                        username="System",
                        message=f"{chose_connection.username}의 {emotion_text} 느껴집니다.",
                    )
                )

        except Exception as e:
            print(e)


@app.on_event("startup")
def startup_event():
    asyncio.create_task(broadcast_emotion_message())
