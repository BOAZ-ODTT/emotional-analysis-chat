import asyncio
import random
import uuid

from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from message import Message

app = FastAPI()
templates = Jinja2Templates(directory="templates")

connection_manager = ConnectionManager()


@app.get("/health")
async def health_check():
    return {"status": "ok"}

class ChatRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.manager = ConnectionManager()
        self.users = set()  # 사용자 수 추적

    async def connect(self, websocket: WebSocket):
        await self.manager.connect(websocket)
        self.users.add(websocket)  # 사용자 추가

    async def disconnect(self, websocket: WebSocket):
        await self.manager.disconnect(websocket)
        self.users.remove(websocket)  # 사용자 제거
        if not self.users:
            del chat_rooms[self.room_id]  # 사용자가 모두 나가면 방 삭제

    async def broadcast(self, message: Message):
        await self.manager.broadcast(message)


chat_rooms = {}


@app.websocket("/chat/connect/new")
async def create_new_chat_room(websocket: WebSocket):
    room_id = str(uuid.uuid4())  # 무작위로 UUID 생성
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
        chat_rooms[room_id].disconnect(websocket)
        if room_id in chat_rooms:
            await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


@app.websocket("/chat/{room_id}/connect")
async def websocket_endpoint(websocket: WebSocket, room_id: str):

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
        chat_rooms[room_id].disconnect(websocket)
        if room_id in chat_rooms:
            await chat_rooms[room_id].broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))



@app.websocket("/chat/connect")
async def websocket_endpoint(
        websocket: WebSocket,
        username: str | None = None,
):
    user = UserConnection(user_id=str(uuid.uuid4()), username=username, websocket=websocket)
    await connection_manager.connect(user)

    try:
        await connection_manager.broadcast(Message(
            username='System', message='누군가 방에 입장했습니다.'
        ))

        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await connection_manager.broadcast(message)
            user.add_message(message)

    except WebSocketDisconnect:
        connection_manager.disconnect(user)
        await connection_manager.broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


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


async def broadcast_emotion_message():
    while True:
        try:
            await asyncio.sleep(20)

            connections = connection_manager.get_connections()
            if not connections:
                continue

            chose_connection: UserConnection = random.choice(connections)

            messages = chose_connection.get_messages()
            if len(messages) == 0:
                await connection_manager.broadcast(
                    Message(
                        username="System",
                        message=f"메시지를 입력해보세요!",
                    )
                )
                continue
            last_message = messages[-1].message

            emotion_text = predict_emotion(last_message)

            await connection_manager.broadcast(
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
