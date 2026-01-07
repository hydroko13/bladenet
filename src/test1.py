import bladenet

client = bladenet.Client('localhost', 8000)
communicator = client.get_communicator()

data = communicator.recv_bytes(2)

print(data)