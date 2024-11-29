import socket

# IP = input("Enter IP: ")
IP = '192.168.1.194'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, 65432))


while True:
    message = input("Enter message: ")
    sock.sendall(message.encode())
    data = sock.recv(1024)
    print(f"Received: {data.decode()}")
    if message == "exit":
        break
