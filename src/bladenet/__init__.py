import socket
import threading

class Server:
    def __init__(self, host_ip, host_port):
        self.host_ip = host_ip
        self.host_port = host_port
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host_ip, self.host_port))
        self.clients = []
        self.broadcasters = []
        self.client_handler_threads = []

    def listen(self):
        self._server_socket.listen()

    
    def block_until_connection(self):
        sock, addr = self._server_socket.accept()
        communicator = Communicator(sock)

        return communicator, addr
    
    def bind_broadcaster(self, trigger, broadcaster):
        self.broadcasters.append(broadcaster)

    def _handle_client(self, communicator, addr):
        communicator
    
    def run(self):
        while True:
            communicator, addr = self.block_until_connection()
            thread = threading.Thread(target=self._handle_client)
            thread.start()
            self.client_handler_threads.append(thread)
            self.clients.append((communicator, addr))




    


class Client:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.connect((self.server_ip, self.server_port))

    
    def get_communicator(self):
        return Communicator(self._server_socket)


class Communicator:
    def __init__(self, sock: socket.socket):
        self._sock = sock

    def send_bytes(self, data):
        self._sock.sendall(data)

    def recv_bytes(self, n):
        data = b""
        while len(data) < n:
            chunk = self._sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError
            data += chunk
        return data
    
    
