from fastapi import FastAPI, Query
from typing import List, Dict
from pydantic import BaseModel
import uvicorn
from hashlib import sha1
from fastapi.responses import JSONResponse

app = FastAPI()

# In-memory store for peers based on torrent info hash
torrents: Dict[str, List[Dict[str, str]]] = {}


@app.get("/announce")
async def announce(
    info_hash: str,
    peer_id: str,
    ip: str,
    port: int,
    uploaded: int,
    downloaded: int,
    left: int,
    event: str | None = None
):
    """Handle GET requests from peers announcing their status to the tracker."""
    info_hash_hex = sha1(info_hash.encode()).hexdigest()

    # Check if the torrent exists in the in-memory database
    if info_hash_hex not in torrents:
        torrents[info_hash_hex] = []

    # Peer data to store
    peer_data = {
        "peer_id": peer_id,
        "ip": ip,
        "port": port,
        "uploaded": uploaded,
        "downloaded": downloaded,
        "left": left
    }

    if event == "started":
        torrents[info_hash_hex].append(peer_data)
        print(f"Peer {peer_id} started and was added to the swarm.")
    elif event == "completed":
        for peer in torrents[info_hash_hex]:
            if peer["peer_id"] == peer_id:
                peer["left"] = 0
                print(f"Peer {peer_id} completed downloading and is now seeding.")
    elif event == "stopped":
        torrents[info_hash_hex] = [peer for peer in torrents[info_hash_hex] if peer["peer_id"] != peer_id]
        print(f"Peer {peer_id} has left the swarm.")

    # Return the list of peers to the requesting peer
    peer_list = [{"ip": peer["ip"], "port": peer["port"]}
                 for peer in torrents[info_hash_hex] if peer["peer_id"] != peer_id]

    return JSONResponse(content={"peers": peer_list})


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
