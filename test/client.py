import asyncio
import websockets
import json
import uuid

TRACKER_URL = "ws://your_ngrok_url/ws"
HTTP_ANNOUNCE_URL = "http://your_ngrok_url/announce"

peer_id = str(uuid.uuid4())

# Example signaling message structure
# {
#     "target_id": "peer_uuid",
#     "message": {
#         "sdp": "...",
#         "type": "offer/answer",
#         "ice": "candidate..."
#     }
# }


async def announce_to_tracker():
    import aiohttp
    async with aiohttp.ClientSession() as session:
        params = {'peer_id': peer_id, 'port': '6881'}
        async with session.get(HTTP_ANNOUNCE_URL, params=params) as resp:
            data = await resp.json()
            return data['peers']


async def handle_messages(websocket):
    async for message in websocket:
        data = json.loads(message)
        sender = data.get('from')
        msg = data.get('message')
        print(f"Received message from {sender}: {msg}")
        # Handle signaling messages here (e.g., SDP, ICE)
        # This would involve interfacing with your WebRTC implementation


async def connect_websocket():
    async with websockets.connect(TRACKER_URL) as websocket:
        # Send initial peer_id
        await websocket.send(json.dumps({'peer_id': peer_id}))

        # Start listening for messages
        consumer_task = asyncio.create_task(handle_messages(websocket))

        # Example: Sending a message to another peer
        # You would trigger this based on your application's logic
        # await websocket.send(json.dumps({
        #     'target_id': 'other_peer_id',
        #     'message': {'sdp': '...', 'type': 'offer'}
        # }))

        await consumer_task


async def main():
    peers = await announce_to_tracker()
    print(f"Discovered peers: {peers}")

    # Connect to WebSocket for signaling
    await connect_websocket()

if __name__ == '__main__':
    asyncio.run(main())
