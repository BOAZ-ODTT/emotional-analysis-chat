from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from message import Message

app = FastAPI()

templates = Jinja2Templates(directory="templates")

manager = ConnectionManager()


@app.websocket("/chat/connect")
async def websocket_endpoint(
        websocket: WebSocket,
):
    await manager.connect(websocket)
    await manager.broadcast(Message(
        username='[System]', message='누군가 방에 입장했습니다.'
    ))

    try:
        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)

            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(Message(username="[System]", message="누군가 방에서 나갔습니다."))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='chat.html',
    )
