import socket
import threading
import miniupnpc
import sys


def get_ip_and_port():
    def setup_upnp(port):
        try:
            # Initialize the UPnP client
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200
            upnp.discover()  # Discover devices
            upnp.selectigd()  # Select the Internet Gateway Device (router)

            # Add a port mapping
            external_ip = upnp.externalipaddress()
            upnp.addportmapping(port, 'TCP', upnp.lanaddr, port, 'BitTorrent', '')
            print(f"Port {port} is mapped. External IP: {external_ip}")
            return external_ip
        except Exception as e:
            print(f"Error setting up UPnP: {e}")
            return None

    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]

    addr = {
        'ip': setup_upnp(port),
        'port': port
    }
    return addr


def handle_client(conn, addr):
    """Handles incoming client connections."""
    print(f"Connected by {addr}")
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Received from client {addr}: {data.decode()}")
            # Echo back the received data
            conn.sendall(data)
    print(f"Connection with {addr} closed.")


def start_server():
    """Starts the server and listens for incoming connections."""
    addr = get_ip_and_port().values()
    external_ip = addr['ip']
    port = addr['port']

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('', port))  # Bind to all interfaces
        server_socket.listen()
        print(f"Server is listening on {external_ip}:{port}")

        while True:
            conn, addr = server_socket.accept()
            # Handle each client connection in a separate thread
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    start_server()
