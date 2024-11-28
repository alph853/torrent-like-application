import asyncio
import json
from aiohttp import web, WSMsgType
import aiohttp_cors

# In-memory storage for connected peers
peers = {}


async def http_announce(request):
    params = request.rel_url.query
    peer_id = params.get('peer_id')
    port = params.get('port')
    if not peer_id or not port:
        return web.Response(text="Missing peer_id or port", status=400)

    # For simplicity, store peer info
    peers[peer_id] = {'ip': request.remote, 'port': port}

    # Respond with list of other peers
    other_peers = [
        {'peer_id': pid, 'ip': info['ip'], 'port': info['port']}
        for pid, info in peers.items() if pid != peer_id
    ]
    return web.json_response({'peers': other_peers})


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Expect the first message to be the peer_id
    msg = await ws.receive()
    if msg.type == WSMsgType.TEXT:
        data = json.loads(msg.data)
        peer_id = data.get('peer_id')
        if not peer_id:
            await ws.close()
            return ws
        peers[peer_id] = {'ws': ws}
        print(f"Peer {peer_id} connected via WebSocket")
    else:
        await ws.close()
        return ws

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                target_id = data.get('target_id')
                message = data.get('message')
                if target_id in peers and 'ws' in peers[target_id]:
                    await peers[target_id]['ws'].send_json({
                        'from': peer_id,
                        'message': message
                    })
            elif msg.type == WSMsgType.ERROR:
                print(f'WebSocket connection closed with exception {ws.exception()}')
    finally:
        del peers[peer_id]
        print(f"Peer {peer_id} disconnected")

    return ws

app = web.Application()
app.router.add_get('/announce', http_announce)
app.router.add_get('/ws', websocket_handler)

# Enable CORS if needed
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
})

for route in list(app.router.routes()):
    cors.add(route)

if __name__ == '__main__':
    web.run_app(app, port=8000)
