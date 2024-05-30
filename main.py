import asyncio
import random
from typing import Optional

from fastapi import FastAPI, Request, Query
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from api import chat_api
from core.dependencies import emotion_classifier, chat_room_manager
from service.chat.user_connection import UserConnection

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# web path와 구분을 위해 /api prefix를 사용합니다.
app.include_router(chat_api.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='chat-room-list.html',
    )


@app.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room(request: Request, room_id: str, username: Optional[str] = Query(None)):
    if username is None:
        return RedirectResponse(url="/")

    chat_room = chat_room_manager.get_chat_room(room_id=room_id)
    if chat_room is None:
        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        request=request,
        name='chat-room.html',
        context={"room_id": room_id, "username": username},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


async def broadcast_emotion_message():
    while True:
        try:
            await asyncio.sleep(20)

            for room in chat_room_manager.list_chat_rooms():
                if room.count_connections() == 0:
                    continue

                user_connection: UserConnection = random.choice(room.list_connections())
                messages = user_connection.list_messages()
                if len(messages) == 0:
                    await chat_room_manager.broadcast_system_message(
                        room_id=room.room_id,
                        message="메시지를 입력해보세요!"
                    )
                    continue

                # 임의로 최근 메시지를 활용
                # 안정성을 위해 글자수 제한이 필요해보이지만 지금은 위험도가 낮은 걸로 판단되어 제한하지 않음
                target_messages = messages[-10:]
                combined_message = "\n".join([message.message for message in target_messages])

                emotion_text = emotion_classifier.classify(combined_message)

                await chat_room_manager.broadcast_system_message(
                    room_id=room.room_id,
                    message=f"{user_connection.username}의 {emotion_text} 느껴집니다."
                )

        except Exception as e:
            print(e)


@app.on_event("startup")
def startup_event():
    asyncio.create_task(broadcast_emotion_message())
