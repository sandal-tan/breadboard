from io import BytesIO
import socket

HOST = "0.0.0.0"
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    print(addr)
    with conn:
        data = BytesIO()

        # Get the client request
        request = conn.recv(4096 * 4)
        print(request.decode())

        conn.sendall("HTTP/1.0 200 OK\r\n".encode())
