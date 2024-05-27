from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MessageType(Enum):
    USER_MESSAGE = "USER_MESSAGE"
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"


class Message(BaseModel):
    username: str
    message: str
    message_type: Optional[MessageType] = None
