import requests

# Local IPFS API endpoint
IPFS_API = "http://127.0.0.1:5001/api/v0"
IPFS_HTTP = "http://127.0.0.1:8080/ipfs/"

def add_text_to_ipfs(text):
    files = {
        'file': ('hello.txt', text)
    }
    response = requests.post(f"{IPFS_API}/add", files=files)
    return response.json()['Hash']

def get_text_from_ipfs(hash):
    response = requests.get(f"https://ipfs.io/ipfs/{hash}")
    return response.text

if __name__ == "__main__":
    hello_string = "Hello, World from IPFS!"
    print("Adding text to IPFS...")

    ipfs_hash = add_text_to_ipfs(hello_string)
    print(f"Added! IPFS Hash: {ipfs_hash}")

