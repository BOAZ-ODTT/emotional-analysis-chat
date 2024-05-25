from connected_user import UserConnection
from message import Message


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[UserConnection] = []

    async def connect(self, connection: UserConnection):
        await connection.accept()
        self.active_connections.append(connection)

    def disconnect(self, connection: UserConnection):
        self.active_connections.remove(connection)

    async def broadcast(self, message: Message):
        for connection in self.active_connections:
            await connection.send_text(message.json())

    async def broadcast_system_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    def get_connections(self):
        return self.active_connections
