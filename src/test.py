import bladenet

server = bladenet.Server('localhost', 8000)

server.listen()

communicator = server.block_until_connection()

communicator.send_bytes(b"HI")

