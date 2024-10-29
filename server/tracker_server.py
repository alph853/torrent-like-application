from fastapi import FastAPI, Query, Request
from typing import List, Dict
from pydantic import BaseModel
import uvicorn
from hashlib import sha1
from fastapi.responses import JSONResponse
from .database import Database, Torrent, Peer
from .utils import to_compact

app = FastAPI()

TORRENT_DATABASE = Database()

@app.get("/announce")
async def announce(
    request: Request,
    info_hash: str,
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

    ip, port = request.client.host, request.client.port
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
    if compact:
        response = to_compact(peer_list)
    else:
        response = JSONResponse(content=peer_list)
    return response


# @app.get("/scrape")
# async def scrape(info_hash: str = Query(...)):
#     """Handle GET requests to scrape data about a torrent."""
#     info_hash_hex = sha1(info_hash.encode()).hexdigest()

#     if info_hash_hex not in torrents:
#         return JSONResponse(content={"error": "Torrent not found"}, status_code=404)

#     # Count seeders and leechers
#     seeders = sum(1 for peer in torrents[info_hash_hex] if peer["left"] == 0)
#     leechers = sum(1 for peer in torrents[info_hash_hex] if peer["left"] > 0)

#     return {
#         "info_hash": info_hash_hex,
#         "complete": seeders,   # Number of seeders
#         "incomplete": leechers  # Number of leechers
#     }

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
