import base64
import bencodepy
from fastapi import FastAPI, Query, Request, Response
from typing import List, Dict
from fastapi.responses import JSONResponse

from database import Database, Torrent, Peer
from utils import to_compact
# from test import db

app = FastAPI()

TORRENT_DATABASE = Database()
# TORRENT_DATABASE = db

INTERVAL = 10


@app.get("/")
async def read_root():
    return 'xyz'


@app.get("/announce")
async def announce(
    request: Request,
    info_hash: str,
    ip: str,
    port: int,
    peer_id: str,
    uploaded: int,
    downloaded: int,
    compact: int,
    left: int | None = None,
    event: str | None = None,
):
    """Handle GET requests from peers announcing their status to the tracker."""
    if TORRENT_DATABASE.get_torrent(info_hash) is None:
        torrent = Torrent(info_hash=info_hash)
        TORRENT_DATABASE.add_torrent(torrent)

    peer = Peer(
        peer_id=peer_id,
        ip=request.client.host,
        port=port,
        uploaded=uploaded,
        downloaded=downloaded,
        left=left,
        status=event,
        info_hash=info_hash,
    )

    if event == "started":
        TORRENT_DATABASE.add_peer(peer)
        print(f"peer {peer_id} has joined the swarm")
    elif event == "completed":
        peer.left = 0
        TORRENT_DATABASE.update_peer(peer)
        print(f"peer {peer_id} has began seeding")
    elif event == "stopped":
        TORRENT_DATABASE.remove_peer(peer)
        print(f"Peer {peer_id} has left the swarm.")
    elif event is None:
        TORRENT_DATABASE.update_peer(peer)
        print(f"Peer {peer_id} has updated their status.")

    # Return the list of peers to the requesting peer
    peer_list = TORRENT_DATABASE.get_torrent_peers(info_hash)
    peer_list = [p for p in peer_list if p.peer_id != peer_id]

    peers_response = to_compact(peer_list) if compact else peer_list

    response = {
        b'interval': INTERVAL,
        b'peers': peers_response
    }

    response = bencodepy.encode(response)
    return Response(content=response, media_type="application/octet-stream")



@app.get("/peers")
async def get_peers(info_hash: str):
    """Return a list of peers for a given torrent."""
    peers = TORRENT_DATABASE.get_torrent_peers(info_hash)
    return JSONResponse(content=peers)


@app.get('/torrents')
async def get_torrents():
    """Return a list of all torrents."""
    torrents = TORRENT_DATABASE.get_torrent()
    return JSONResponse(content=torrents)
