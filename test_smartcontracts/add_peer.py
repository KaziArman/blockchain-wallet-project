from web3 import Web3
import sys

my_port = int(sys.argv[1])
peer_enode = sys.argv[2]

# Connect to your Ethereum node
w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{my_port}"))


# Add the peer
result = w3.provider.make_request("admin_addPeer", [peer_enode])

print(f"Peer added: {result}")

peers = w3.provider.make_request("admin_peers", [])["result"]
print(f"Current Peers: {peers}")