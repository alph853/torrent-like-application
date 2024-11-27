# server.py

from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict
import uvicorn
import logging
import ipaddress
import socket
import struct

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory storage for peers
peers: Dict[str, Dict] = {}


class PeerRegister(BaseModel):
    peer_id: str = Field(..., description="Unique identifier for the peer")
    port: int = Field(..., ge=1, le=65535, description="Port number the peer is listening on")


class PeerInfo(BaseModel):
    peer_id: str
    ip: str
    port: int


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_peer(request: Request, peer: PeerRegister):
    """
    Register a new peer with the tracker.
    """
    # Extract the client's IP address, considering proxy headers
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs, the first is the original client
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host

    logging.info(f"Registering peer: ID={peer.peer_id}, IP={client_ip}, Port={peer.port}")

    # Validate IP version
    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        logging.error(f"Invalid IP address received: {client_ip}")
        raise HTTPException(status_code=400, detail="Invalid IP address.")

    # Store the peer's information
    peers[peer.peer_id] = {
        "peer_id": peer.peer_id,
        "ip": client_ip,
        "port": peer.port
    }

    logging.info(f"Current number of registered peers: {len(peers)}")

    return {"status": "registered", "peer_id": peer.peer_id}


@app.get("/peers", response_model=List[PeerInfo])
async def get_peers(peer_id: str):
    """
    Retrieve a list of all registered peers excluding the requesting peer.
    """
    if peer_id not in peers:
        logging.warning(f"Peer ID {peer_id} not found when requesting peers.")
        raise HTTPException(status_code=404, detail="Peer not registered.")

    # Exclude the requesting peer from the list
    other_peers = [
        PeerInfo(peer_id=peer["peer_id"], ip=peer["ip"], port=peer["port"])
        for pid, peer in peers.items() if pid != peer_id
    ]

    logging.info(f"Peer {peer_id} requested list of peers. Returning {len(other_peers)} peers.")

    return other_peers


@app.delete("/remove/{peer_id}", status_code=status.HTTP_200_OK)
async def remove_peer(peer_id: str):
    """
    Remove a peer from the tracker.
    """
    if peer_id in peers:
        del peers[peer_id]
        logging.info(f"Removed peer with ID: {peer_id}")
        return {"status": "removed", "peer_id": peer_id}
    else:
        logging.warning(f"Attempted to remove non-existent peer ID: {peer_id}")
        raise HTTPException(status_code=404, detail="Peer not found")


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    # Run the app with Uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
