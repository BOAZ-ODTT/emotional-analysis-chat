import asyncio
import random
import uuid

from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from connected_user import UserConnection
from connection_manager import ConnectionManager
from inference import predict_emotion
from message import Message

app = FastAPI()
templates = Jinja2Templates(directory="templates")

connection_manager = ConnectionManager()


# 입장 버튼 누른 이후
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

    except WebSocketDisconnect:
        connection_manager.disconnect(user)
        await connection_manager.broadcast(Message(username="System", message="누군가 방에서 나갔습니다."))


# root
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='chat.html',
    )


async def broadcast_emotion_message():
    while True:
        await asyncio.sleep(30)

        connections = connection_manager.get_connections()
        if not connections:
            continue

        chose_connection: UserConnection = random.choice(connections)

        messages = chose_connection.get_messages()
        last_message = messages[-1].message

        emotion_text = predict_emotion(last_message)

        await connection_manager.broadcast(
            Message(
                username="System",
                message=f"누군가의 {emotion_text} 느껴집니다.",
            )
        )


@app.on_event("startup")
def startup_event():
    asyncio.create_task(broadcast_emotion_message())
