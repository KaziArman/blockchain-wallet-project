import requests
from urllib.parse import urlparse

def IPFS_findNodeID(ip, rest_port, discovery_port, protocol="http"):

    request_url = "{}://{}:{}/api/v0/id".format(protocol, ip, str(rest_port))
    url = urlparse(request_url)

    response = requests.post(url.geturl(), headers={'content-type': 'application/json'})

    if response.status_code != 201 and response.status_code != 200:
        return {"error": True, "response": response.text}

    ret_dict = response.json()

    ipfs_id = ret_dict["ID"]

    ipfs_peer_id = "/ip4/{}/tcp/{}/p2p/{}".format(str(ip), str(discovery_port), ipfs_id)

    return ipfs_peer_id


def IPFS_addPeer(peernode, ip, port, protocol="http"):

    print("{}:{} is adding {} as peer".format(ip, port, peernode))

    # http://127.0.0.1:5001/api/v0/swarm/connect?arg=<address>
    request_url = "{}://{}:{}/api/v0/swarm/connect".format(protocol, ip, str(port))
    url = urlparse(request_url)

    payload = {'arg': peernode}
    response = requests.post(url.geturl(), params=payload, headers={'content-type': 'application/json'})
    if response.status_code == 201 or response.status_code == 200:
        return {"error": False, "response": response.text}
    else:
        return {"error": True, "response": response.text}

if __name__ == "__main__":
    #replace this with your existing ip
    localIP = "127.0.0.1"
    localIPFS_rest_port = "5001"
    localIPFS_disc_port = "4001"
    ipfs_address = IPFS_findNodeID(localIP,localIPFS_rest_port,localIPFS_disc_port)
    print(ipfs_address)

    node2_IP = "127.0.0.1"
    node2_rest_port = "5002"
    return_val = IPFS_addPeer(ipfs_address, node2_IP, node2_rest_port)
    print(return_val)