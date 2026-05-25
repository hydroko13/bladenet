import socket
import struct
import threading
import random
import time


class Server:
    def __init__(self, addr):
        self.addr = addr
        self.packets = []
        

    def __enter__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(self.addr)
        self.s.setblocking(False)
        return self
    

    
    def process(self):
        try:
            data, addr = self.s.recvfrom(1024)

            if data[:1] == b'R':
                packet_id, = struct.unpack('!H', data[1:3])
                packet_payload = data[3:]

                print(packet_id)

                self.s.sendto(b"A" + struct.pack("!H", packet_id), self.addr)

                self.packets.append((packet_payload, addr))

            elif data[:1] == b'U':
                packet_payload = data[1:]
                self.packets.append((packet_payload, addr))
        except ConnectionResetError:
            pass
        except BlockingIOError:
            pass

    
    def send_reliable(self, data):
        self.s.sendto(b'R' + data, self.server_addr)

    def send_unreliable(self, data):
        self.s.sendto(b'U' + data, self.server_addr)


    def events(self):
        while len(self.packets) > 0:
            yield self.packets.pop(0)
        
        
    
    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.s.close()

class Client:
    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.packets = []
        self.packets_pending_acks = {}
        self.next_packet_id = 0


    def __enter__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setblocking(False)
        

        return self
    
    def process(self):
        try:
            data, addr = self.s.recvfrom(1024)

            if data[:1] == b'R':
                packet_id, r = struct.unpack('!HI', data[1:7])
                packet_payload = data[7:]

                print(packet_id)

                self.s.sendto(b"A" + struct.pack("!HI", packet_id, r), self.server_addr)

                self.packets.append((packet_payload, addr))

            elif data[:1] == b'U':
                packet_payload = data[1:]
                self.packets.append((packet_payload, addr))

            elif data[:1] == b'A':
                packet_id, r = struct.unpack('!HI', data[1:])
                
                del self.packets_pending_acks[(packet_id, r)]


                self.packets.append((packet_payload, addr))


        except ConnectionResetError:
            pass
        except BlockingIOError:
            pass

    def send_reliable(self, data):
        r = random.randint(0, 4294967295)
        self.packets_pending_acks[(self.next_packet_id, r)] = (data, time.time_ns())
        self.s.sendto(b'R' + struct.pack("!HI", self.next_packet_id, r) + data, self.server_addr)
        self.next_packet_id += 1
        if self.next_packet_id > 65535:
            self.next_packet_id = 0

    def send_unreliable(self, data):
        self.s.sendto(b'U' + data, self.server_addr)

    
    def events(self):
        while len(self.packets) > 0:
            yield self.packets.pop(0)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.s.close()

def create_server(addr):
    return Server(addr)

def connect_to(addr):
    return Client(addr)