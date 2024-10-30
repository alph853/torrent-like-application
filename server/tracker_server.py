from fastapi import FastAPI, Query, Request
from typing import List, Dict
from fastapi.responses import JSONResponse

from .database import Database, Torrent, Peer
from .utils import to_compact, from_compact
from .test import db

app = FastAPI()

TORRENT_DATABASE = Database()
TORRENT_DATABASE = db


@app.get("/announce")
async def announce(
    info_hash: str,
    ip: str,
    port: int,
    peer_id: str,
    uploaded: int,
    downloaded: int,
    left: int,
    compact: int,
    event: str | None = None,
):
    """Handle GET requests from peers announcing their status to the tracker."""
    if TORRENT_DATABASE.get_torrent(info_hash) is None:
        return JSONResponse(content={"error": "Torrent not found"}, status_code=404)

    peer = Peer(
        peer_id=peer_id,
        ip=ip,
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

    # Return the list of peers to the requesting peer
    peer_list = TORRENT_DATABASE.get_torrent_peers(info_hash)
    peer_list = [p for p in peer_list if p.peer_id != peer_id]
    if compact:
        response = to_compact(peer_list)
    else:
        response = JSONResponse(content=peer_list)
    return response


@app.get("/")
def read_root():
    return {"Hello": "World"}
