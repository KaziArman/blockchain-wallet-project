import requests, pickle
import numpy as np

# Local IPFS API endpoint
IPFS_API = "http://127.0.0.1:5001/api/v0"
IPFS_HTTP = "http://127.0.0.1:8080/ipfs/"


array = np.random.rand(3, 3)
pickled_array = pickle.dumps(array)

files = {'file': ('array.pkl', pickled_array)}
res = requests.post(f"{IPFS_API}/add", files=files)
cid = res.json()['Hash']

print(f"Dumped array {array} to pickle {pickled_array} to IPFS with cid:{cid}")

print(f"Now extracting CID.....")

res = requests.post(f"{IPFS_API}/cat", params={'arg': cid})
restored_pickled_array = res.content

restored_array = pickle.loads(restored_pickled_array)

print(restored_array,array)



