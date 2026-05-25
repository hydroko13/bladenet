import random
import bladenet as bn

with bn.connect_to(('127.0.0.1', 8988)) as client:
    client.send_packet_udp(b'Hi')

    
