import bladenet as bn
import time

with bn.create_server(('127.0.0.1', 8988)) as server:
    expected = 0
    while True:
        server.process()
        
        
        for payload, addr in server.events():
            print("Got", payload, 'from', addr)
        time.sleep(0.02)

