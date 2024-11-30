import socket

# IP = input("Enter IP: ")
IP = '10.128.49.47'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, 12000))


while True:
    message = input("Enter message: ")
    sock.sendall(message.encode())
    data = sock.recv(1024)
    print(f"Received: {data.decode()}")
    if message == "exit":
        break
