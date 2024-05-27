import asyncio
import random

from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from api import chat_api
from service.chat.chat_room_manager import chat_rooms
from service.chat.user_connection import UserConnection
from core.dependencies import emotion_classifier

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# web path와 구분을 위해 /api prefix를 사용합니다.
app.include_router(chat_api.router, prefix="/api")


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
