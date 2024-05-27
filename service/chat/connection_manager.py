from service.chat.message import Message, MessageType
from service.chat.user_connection import UserConnection


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[UserConnection] = []

    async def connect(self, connection: UserConnection):
        await connection.accept()
        self.active_connections.append(connection)

    def disconnect(self, connection: UserConnection):
        self.active_connections.remove(connection)

    async def broadcast_system_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_message(
                Message(
                    username="System",
                    message=message,
                    message_type=MessageType.SYSTEM_MESSAGE,
                ),
            )

    async def broadcast(self, message: Message):
        for connection in self.active_connections:
            await connection.send_message(message)

    def get_connections(self):
        return self.active_connections

    def count_connections(self):
        return len(self.active_connections)
