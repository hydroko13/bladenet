import socket
import struct
import random
import time
from collections import deque


# Packet format:
#   R: reliable packet
#      b'R' + uint16(packet_id) + uint32(token) + payload
#   A: ack
#      b'A' + uint16(packet_id) + uint32(token)
#   U: unreliable packet
#      b'U' + payload

RELIABLE_HEADER = struct.Struct("!HI")  # uint16, uint32
ACK_RETRY_NS = 50_000_000               # 50 ms
CLEANUP_AFTER_NS = 60_000_000_000       # 60 s


class _ReliableEndpoint:
    def __init__(self):
        self.packets = deque()
        self.packets_pending_acks = {}   # (peer_addr, packet_id, token) -> (data, last_send_ns)
        self.received_reliable = {}      # (peer_addr, packet_id, token) -> first_seen_ns
        self.next_packet_id = 0

    def _next_id(self):
        pid = self.next_packet_id
        self.next_packet_id = (self.next_packet_id + 1) & 0xFFFF
        return pid

    def _make_token(self):
        return random.getrandbits(32)

    def _recv_all(self, sock):
        while True:
            try:
                data, addr = sock.recvfrom(4096)
            except BlockingIOError:
                break
            except ConnectionResetError:
                continue

            if not data:
                continue

            packet_type = data[:1]

            if packet_type == b'R':
                if len(data) < 1 + RELIABLE_HEADER.size:
                    continue

                packet_id, token = RELIABLE_HEADER.unpack(data[1:1 + RELIABLE_HEADER.size])
                payload = data[1 + RELIABLE_HEADER.size:]
                key = (addr, packet_id, token)

                # Always ACK reliable packets, even duplicates.
                sock.sendto(b"A" + RELIABLE_HEADER.pack(packet_id, token), addr)

                # Only deliver the payload once.
                if key not in self.received_reliable:
                    self.received_reliable[key] = time.monotonic_ns()
                    self.packets.append((payload, addr))

            elif packet_type == b'U':
                payload = data[1:]
                self.packets.append((payload, addr))

            elif packet_type == b'A':
                if len(data) < 1 + RELIABLE_HEADER.size:
                    continue

                packet_id, token = RELIABLE_HEADER.unpack(data[1:1 + RELIABLE_HEADER.size])
                key = (addr, packet_id, token)
                self.packets_pending_acks.pop(key, None)

    def _resend_pending(self, sock):
        now = time.monotonic_ns()

        for key, (data, last_send_ns) in list(self.packets_pending_acks.items()):
            if now - last_send_ns >= ACK_RETRY_NS:
                peer_addr, packet_id, token = key
                sock.sendto(
                    b"R" + RELIABLE_HEADER.pack(packet_id, token) + data,
                    peer_addr,
                )
                self.packets_pending_acks[key] = (data, now)

    def _cleanup_old_received(self):
        now = time.monotonic_ns()
        for key, seen_ns in list(self.received_reliable.items()):
            if now - seen_ns > CLEANUP_AFTER_NS:
                del self.received_reliable[key]

    def events(self):
        while self.packets:
            yield self.packets.popleft()


class Server(_ReliableEndpoint):
    def __init__(self, addr):
        super().__init__()
        self.addr = addr

    def __enter__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(self.addr)
        self.s.setblocking(False)
        return self

    def process(self):
        self._recv_all(self.s)
        self._resend_pending(self.s)
        self._cleanup_old_received()

    def send_reliable(self, addr, data):
        packet_id = self._next_id()
        token = self._make_token()
        key = (addr, packet_id, token)
        now = time.monotonic_ns()

        self.packets_pending_acks[key] = (data, now)
        self.s.sendto(b"R" + RELIABLE_HEADER.pack(packet_id, token) + data, addr)

    def send_unreliable(self, addr, data):
        self.s.sendto(b"U" + data, addr)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.s.close()


class Client(_ReliableEndpoint):
    def __init__(self, server_addr):
        super().__init__()
        self.server_addr = server_addr

    def __enter__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 0))
        self.s.setblocking(False)
        return self

    def process(self):
        self._recv_all(self.s)
        self._resend_pending(self.s)
        self._cleanup_old_received()

    def send_reliable(self, data):
        packet_id = self._next_id()
        token = self._make_token()
        key = (self.server_addr, packet_id, token)
        now = time.monotonic_ns()

        self.packets_pending_acks[key] = (data, now)
        self.s.sendto(b"R" + RELIABLE_HEADER.pack(packet_id, token) + data, self.server_addr)

    def send_unreliable(self, data):
        self.s.sendto(b"U" + data, self.server_addr)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.s.close()


def create_server(addr):
    return Server(addr)

def connect_to(addr):
    return Client(addr)