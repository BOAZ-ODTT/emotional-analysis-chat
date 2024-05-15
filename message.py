from pydantic import BaseModel


class Message(BaseModel):
    username: str
    message: str
