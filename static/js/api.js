const apiEndpoint = `${window.location.origin}/api/v1`;
const socketEndpoint = apiEndpoint.replace('http', 'ws');

async function fetchChatRooms() {
    const response = await fetch(`${apiEndpoint}/chat/rooms`);

    return await response.json();
}

async function fetchChatRoom(roomId) {
    const response = await fetch(`${apiEndpoint}/chat/rooms/${roomId}`);

    return await response.json();
}

async function createChatRoom(name) {
    const response = await fetch(`${apiEndpoint}/chat/rooms/new`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({name}),
    });

    return await response.json();
}


async function connectChatRoomSocket(roomId, username) {
    return new WebSocket(`${socketEndpoint}/chat/${roomId}/connect/${username}`);
}
