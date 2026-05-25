import bladenet as bn
import time

with bn.create_server(('127.0.0.1', 8988)) as server:
    expected = 0
    while True:
        server.process()
        
        
        for event in server.events():
            print(event)
        time.sleep(0.02)

