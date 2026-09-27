from web3 import Web3
import sys

ip = sys.argv[1]
port = sys.argv[2]

HTTP_URL = f"http://{ip}:{port}"

web3 = Web3(Web3.HTTPProvider(HTTP_URL))
enode_address = web3.provider.make_request("admin_nodeInfo", []).get("result",{}).get("enode","ENODE_NOT_FOUND")
print(enode_address)