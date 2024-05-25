import asyncio
import random
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from message import Message

app = FastAPI()
templates = Jinja2Templates(directory="templates")

manager = ConnectionManager()

class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.manager = ConnectionManager()

    async def connect(self, websocket: WebSocket):
        await self.manager.connect(websocket)

    async def disconnect(self, websocket: WebSocket):
        await self.manager.disconnect(websocket)

    async def broadcast(self, message: Message):
        await self.manager.broadcast(message)


chat_rooms = {}


@app.websocket("/chat/{room_id}/connect")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    if room_id not in chat_rooms:
        chat_rooms[room_id] = ChatRoom(room_id)

    await chat_rooms[room_id].connect(websocket)

    try:
        await chat_rooms[room_id].broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await chat_rooms[room_id].broadcast(message)
    except WebSocketDisconnect:
        await chat_rooms[room_id].disconnect(websocket)
        await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


@app.websocket("/chat/new/connect")
async def create_new_chat_room(websocket: WebSocket):
    room_id = str(uuid.uuid4())  # 무작위로 UUID 생성
    if room_id not in chat_rooms:
        chat_rooms[room_id] = ChatRoom(room_id)

    await chat_rooms[room_id].connect(websocket)

    try:
        await chat_rooms[room_id].broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await chat_rooms[room_id].broadcast(message)
    except WebSocketDisconnect:
        await chat_rooms[room_id].disconnect(websocket)
        await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


# 입장 버튼 누른 이후
@app.websocket("/chat/connect")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        await manager.broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


# root
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='chat.html',
    )


async def broadcast_emotion_message():
    emotion_messages = ["불안이", "당황이", "분노가", "슬픔이", "중립이", "행복이", "혐오가"]
    while True:
        await asyncio.sleep(30)

        random_emotion_text = random.choice(emotion_messages)
        await manager.broadcast(
            Message(
                username="System",
                message=(f"누군가의 {random_emotion_text} 느껴집니다."),
            )
        )


@app.on_event("startup")
def startup_event():
    asyncio.create_task(broadcast_emotion_message())
