import socket


def start_server(host='0.0.0.0', port=65432):
    """
    Starts a TCP server that listens for incoming connections.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}")
        print(f"Server host ip: {socket.gethostbyname(socket.gethostname())}")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"Received from {addr}: {data.decode()}")
                    conn.sendall(data)  # Echo back the received data


if __name__ == "__main__":
    start_server()
