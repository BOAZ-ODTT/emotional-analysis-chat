from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MessageType(Enum):
    USER_MESSAGE = "USER_MESSAGE"
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"


class MessageEventType(Enum):
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"


class Message(BaseModel):
    user_id: Optional[str] = None
    username: str
    message: str
    message_type: Optional[MessageType] = None
    event_type: Optional[MessageEventType] = None
    sent_at: Optional[datetime] = datetime.now()
