# client.py

import ipaddress
import requests
import socket
import threading
import time
from typing import List
from pydantic import BaseModel

# Define the PeerInfo model using Pydantic for structured data


class PeerInfo(BaseModel):
    peer_id: str
    ip: str
    port: int


TRACKER_URL = "https://10diembtl.ngrok.app"  # Replace with your ngrok HTTPS URL
PEER_ID = "peer1"  # Unique identifier for this peer (change for each client)
PEER_PORT = 5000    # Port this peer will listen on (change for each client)


def is_ipv4(ip: str) -> bool:
    """
    Determines if the given IP address is IPv4.
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except ValueError:
        return False


def is_ipv6(ip: str) -> bool:
    """
    Determines if the given IP address is IPv6.
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except ValueError:
        return False


def listen_for_connections_ipv4():
    """
    Listens for incoming IPv4 connections and handles them.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', PEER_PORT))  # Bind to all IPv4 interfaces
    server_socket.listen()
    print(f"[{PEER_ID}] Listening for incoming connections on port {PEER_PORT} (IPv4)...")

    while True:
        try:
            conn, addr = server_socket.accept()
            print(f"[{PEER_ID}] Connected by {addr} (IPv4)")
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[{PEER_ID}] Error accepting IPv4 connection: {e}")


def listen_for_connections_ipv6():
    """
    Listens for incoming IPv6 connections and handles them.
    """
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # On some systems, you may need to set IPV6_V6ONLY to 1 to restrict to IPv6
    # server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    server_socket.bind(('', PEER_PORT))  # Bind to all IPv6 interfaces
    server_socket.listen()
    print(f"[{PEER_ID}] Listening for incoming connections on port {PEER_PORT} (IPv6)...")

    while True:
        try:
            conn, addr = server_socket.accept()
            print(f"[{PEER_ID}] Connected by {addr} (IPv6)")
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[{PEER_ID}] Error accepting IPv6 connection: {e}")


def handle_client(conn: socket.socket, addr):
    """
    Handles communication with a connected peer.
    """
    with conn:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[{PEER_ID}] Connection closed by {addr}")
                    break
                message = data.decode()
                print(f"[{PEER_ID}] Received from {addr}: {message}")
                # Echo the message back
                conn.sendall(data)
            except Exception as e:
                print(f"[{PEER_ID}] Error handling client {addr}: {e}")
                break


def register_with_tracker():
    """
    Registers the peer with the rendezvous server.
    """
    url = f"{TRACKER_URL}/register"
    payload = {
        "peer_id": PEER_ID,
        "port": PEER_PORT
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            print(f"[{PEER_ID}] Successfully registered with tracker.")
        else:
            print(f"[{PEER_ID}] Failed to register with tracker: {response.text}")
    except Exception as e:
        print(f"[{PEER_ID}] Error registering with tracker: {e}")


def get_peers() -> List[PeerInfo]:
    """
    Retrieves the list of other peers from the tracker.
    """
    url = f"{TRACKER_URL}/peers"
    params = {"peer_id": PEER_ID}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            peers_data = response.json()
            # Validate and parse peer data using Pydantic
            peers = [PeerInfo(**peer) for peer in peers_data]
            return peers
        else:
            print(f"[{PEER_ID}] Failed to retrieve peers: {response.text}")
            return []
    except Exception as e:
        print(f"[{PEER_ID}] Error retrieving peers: {e}")
        return []


def connect_to_peer(peer: PeerInfo):
    """
    Connects to another peer using the appropriate socket based on IP version.
    """
    peer_ip = peer.ip
    peer_port = peer.port
    try:
        if is_ipv4(peer_ip):
            family = socket.AF_INET
            address = (peer_ip, peer_port)
        elif is_ipv6(peer_ip):
            family = socket.AF_INET6
            address = (peer_ip, peer_port, 0, 0)  # flowinfo and scopeid set to 0
        else:
            print(f"[{PEER_ID}] Invalid IP address format for peer {peer.peer_id}: {peer_ip}")
            return

        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Optional: set a timeout for the connection attempt
            s.connect(address)
            print(f"[{PEER_ID}] Connected to peer {peer.peer_id} at {peer_ip}:{peer_port}")
            message = f"Hello from {PEER_ID}"
            s.sendall(message.encode())
            print(f"[{PEER_ID}] Sent to {peer.peer_id}: {message}")
            data = s.recv(1024)
            if data:
                print(f"[{PEER_ID}] Received from {peer.peer_id}: {data.decode()}")
            else:
                print(f"[{PEER_ID}] No response from {peer.peer_id}")
    except Exception as e:
        print(f"[{PEER_ID}] Failed to connect to peer {peer.peer_id} at {peer_ip}:{peer_port} - {e}")


def main():
    # Start listening for incoming IPv4 connections
    threading.Thread(target=listen_for_connections_ipv4, daemon=True).start()

    # Start listening for incoming IPv6 connections
    threading.Thread(target=listen_for_connections_ipv6, daemon=True).start()

    # Register with the tracker
    time.sleep(1)  # Brief pause to ensure the listening threads are up
    register_with_tracker()

    # Wait a moment before fetching peers
    time.sleep(2)

    # Retrieve peers
    peers = get_peers()
    if not peers:
        print(f"[{PEER_ID}] No other peers found.")
    else:
        print(f"[{PEER_ID}] Found {len(peers)} peer(s). Attempting to connect...")
        for peer in peers:
            if peer.peer_id == PEER_ID:
                continue  # Skip connecting to self if present
            threading.Thread(target=connect_to_peer, args=(peer,), daemon=True).start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{PEER_ID}] Shutting down client.")


if __name__ == "__main__":
    main()
