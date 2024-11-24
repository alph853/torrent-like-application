import socket
import threading

# Server configuration
HOST = "0.0.0.0"  # Listen on all network interfaces
PORT = 12345

# Function to handle communication with a client


def handle_client(client_socket, client_address):
    print(f"[NEW CONNECTION] {client_address} connected.")
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')  # Receive message
            if not message:
                break
            print(f"[{client_address}] {message}")
            # Echo the message back to the client
            client_socket.send(f"Server received: {message}".encode('utf-8'))
        except ConnectionResetError:
            print(f"[DISCONNECTED] {client_address} disconnected.")
            break
    client_socket.close()

# Main server function


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        client_socket, client_address = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True)
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == "__main__":
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    print(ip)
    start_server()
