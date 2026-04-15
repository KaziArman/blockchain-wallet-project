## Prerequisites for new devices
  ```powershell
  docker pull hyperledger/besu:latest
  docker pull pramanan3/smartcontract_test:latest
  docker pull alpine:3.19.0
  ```

Before doing anything follow the Windows Firewall step from `WS_Firewall.MD`

First make sure the Node 1 and Node2, and networkfiles folder is empty.
## Use:- docker compose up clean-data -d
Most proper way to do is, open git bash termnial from the + terminal window then go to the QBFT-Network directory, then run:-
## bash clean.sh


Then to launce the blockchain node for the very first time, 
First use command `ipconfig` to find your ipv4 address, under the Wireless LAN adapter Wi-Fi:
look for 
   IPv4 Address. . . . . . . . . . . : 192.168.1.239
then update the `- --p2p-host=` from `docker-compose.yml's qbft-launch-bootnode1 service` with the IPV4 address that you found for your device's wifi router.

Now before running the next command, On Windows, Docker runs inside a WSL2 Linux VM. network_mode: "host" binds to the VM's network, NOT your WiFi interface. This means other devices on your WiFi cannot reach your node — even with the firewall completely disabled.
Always use explicit ports mappings instead. Docker Desktop correctly forwards mapped ports from the Windows host to the container. This was the root cause of all connectivity failures during our setup.

while launcing each bootnode, instead of `network_mode: "host"` use:
    ports:
      - "30303:30303/tcp"
      - "30303:30303/udp"
      - "8545:8545"
and also add these command in the the same bootnode:
      - --rpc-http-host=0.0.0.0

Then Open PowerShell:
```powershell
ipconfig
```
 
Look under **Wireless LAN adapter Wi-Fi** for:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.239
```
Write this down — we call it `DEVICE1_IP` throughout this guide. In our tested setup, this was `192.168.1.239`. Then in `  qbft-launch-bootnode1` change the p2p-host with the IPV4 address you just found.
      `- --p2p-host=192.168.1.239`

Then use genesis to launce. Before launching make sure you have deleted the networkfiles folder under QBFT-network (which is already done by running clean.sh)

## docker compose up qbft-configure-genesis

You must get the following structure
QBFT-Network/
├── qbftConfigFile.json
├── docker-compose.yml
├── clean.sh
├── networkFiles
│     ├── data
│         ├── keys
│             ├── <public-key-file (like 0xf7224f3aae8f9e1d0d082dd5ecae992e916e9686)>

After configuring genesis, use:- 
## docker compose up move-keys

You will now get
QBFT-Network/
├── qbftConfigFile.json
├── docker-compose.yml
├── clean.sh
├── networkFiles
│     ├── data
│         ├── keys
│             ├── <public-key-file (like 0xf7224f3aae8f9e1d0d082dd5ecae992e916e9686)>
├── Node-1
│   ├── data
│   │    ├── key
│   │    ├── key.pub

THEN RUN:-
## docker compose up qbft-launch-bootnode1

After running the above command in the terminal, you will get the enode URL as the output, copy it and save it as a text file, ` it's very important ` , you will need it later.

qbft-launch-bootnode1-1  | 2026-04-14 06:52:35.941+0000 | main | INFO  | DefaultP2PNetwork | `Enode URL enode://9dda35532bc67ef23b00c2cf246447ef9c79926ae3796fb3c0067278530521bb31d417774b8bc18893b53e689baf907fd04f0d406699c829321dda7da36aadd0@192.168.1.239:30303`

Keep this terminal running. Open a new terminal for the next steps.

Run this command `Test-NetConnection 192.168.1.239 -Port 30303` and `Test-NetConnection 192.168.1.239 -Port 8545` to see if the host is broadcasting the node. you should get this output: `TcpTestSucceeded : True`

Then run `docker compose up test-smartcontracts -d` to turn on the test-smartcontracts container. 

Then deplot Smart Contract by running the command `docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 1 8545"` and you must see something like this:
```commandline
Compilation successful! ABI and Bytecode saved.
Deploying contract... Tx Hash: c4e9d650c2ce95c4f4ee0a9e52f469c56319f5f735dcb28969cfedfba60b9872
Contract deployed at: 0x10626FA93259c3C0b6f609ebc354dEa734Cb6d9a
Current Message: Hello, World!
Updating message... Tx Hash: 75ce38107ff6803b0b7604e7a1df633798d5527b61979bff15280af55f78f76b
Current Message: Hello to you too!

```
## Folder Structure (Both Devices)
 
```
blockchain_tutorial/
├── qbft/
│   └── QBFT-Network/
│       ├── qbftConfigFile.json       ← Unchanged, same on both
│       ├── docker-compose.yml        ← DIFFERENT per device
│       ├── clean.sh                  ← Device 1 only
│       ├── networkFiles/             ← Generated on Device 1, copied to Device 2
│       │   ├── genesis.json
│       │   └── keys/
│       │       └── <public-key-folder>/
│       ├── Node1/                    ← Device 1 only
│       │   └── data/
│       │       ├── key
│       │       └── key.pub
│       ├── Node2/                    ← Device 2 (or Device 1 if running locally)
│       │   └── data/
│       └── Node3/                    ← Device 1 only (optional extra node)
│           └── data/
└── test_smartcontracts/              ← Must exist on both devices
    ├── compile_SC_qbft.py
    ├── find_enode_address.py
    ├── add_peer.py
    ├── hello_world.sol
    ├── abi.json                      ← Generated while running compile_SC_qbft.py
    ├── compiled_code.json            ← Generated while running compile_SC_qbft.py
    └── contract_address.json         ← Generated while running compile_SC_qbft.py
```

## By doing all the above steps we are making sure a blockchain system is created in the host.


### Now to launch bootnode2 in another device, from the host machine, we can broadcast all the changed file so that other machine can download it and save it on their local before changing the docker-compose.yml and running bootnode2 command

In the host machine, add another terminal and write the underneath code in the terminal `python3 -m http.server 8000`, then look for the ipv4 address from the host machine and create a weblink (`http:192.168.1.239:8000`) and share it to other users within the same wifi router. Your copied foloders structure should look like this:

blockchain_tutorial/
├── qbft/
│   └── QBFT-Network/
│       ├── docker-compose.yml     ← Device 2 version
│       ├── networkFiles/          ← Copied from Device 1
│       │   ├── genesis.json
│       │   └── keys/
│       └── Node2/
│           └── data/              ← Create this empty folder
└── test_smartcontracts/           ← Copied from Device 1

Basically everything from networkFiles and `abi.json`, `compiled_code.json`, and `contract_address.json` from the test_smartcontracts. To be safe, copy the whole folder.

Now, Find Device 2's IP Address
 
```powershell
ipconfig
```
 
In our tested setup, Device 2 was `192.168.1.11`.

## Now update the  docker-compose.yml files launch bootnode2 service.

Open `docker-compose.yml` and in `qbft-launch-node2` service replace:
 
1. `<ENODE_URL>` → Full enode we found after launching bootnode1, for example:
   ```
   enode://c0c0e730f0c72c3199e164aa476ad90e4ecb958889c1000241febbb8a2f878169ba25b393870667bb42f177cdf90664b94beec07e5b0ab1a23aadfa95f49cb70@192.168.1.239:30303
   ```
2. `<DEVICE2_IP>` → This device's WiFi IPv4, for example: `192.168.1.11`, and change the `- --p2p-host=192.168.1.11`

3. instead of `network_mode: "host"` use:
    ports:
      - "30303:30303/tcp"
      - "30303:30303/udp"
      - "8545:8545"
and also add these command in the the same bootnode:
      - --rpc-http-host=0.0.0.0

Before launching, confirm Device 2 can reach Device 1:
```powershell
ping 192.168.1.239
Test-NetConnection 192.168.1.239 -Port 30303
```
 
Both must succeed. If the port test fails, check Device 1's firewall.

## IF I WANT TO RUN BOOTNODE2 FROM THE SAME MACHINE WITHIN THE SAME WIFI ROUTER, THE p2p host info will be the same as the IP address of device1

The change in the bootnode2 on the same device would be the underneath:

1. - --bootnodes=enode://9dda35532bc67ef23b00c2cf246447ef9c79926ae3796fb3c0067278530521bb31d417774b8bc18893b53e689baf907fd04f0d406699c829321dda7da36aadd0@192.168.1.239:30303

2. - --p2p-host=192.168.1.239

3. instead of `network_mode: "host"` use:
    ports:
      - "30304:30304/tcp"
      - "30304:30304/udp"
      - "8546:8546"
and also add these command in the the same bootnode:
      - --rpc-http-host=0.0.0.0
and change the underenaths:
      - --p2p-port=30304
      - --rpc-http-port=8546

## Now that I have `qbft-launch-node2` updated in `docker-compose.yml` file, run:
 `docker compose up qbft-launch-node2` to launch Node2

 **Expected output from Node2 device** — Node2 syncs all existing blocks, then follows new ones:
```
qbft-launch-node2-1  | ... Imported empty block #170 / 0 tx ... Peers: 1
qbft-launch-node2-1  | ... Imported empty block #171 / 0 tx ... Peers: 1
```

**If Node2 does NOT connect** (no `Peers: 1` after 30 seconds), manually add the peer. Open a **new terminal**:
```powershell
docker compose up test-smartcontracts -d
docker exec -it qbft-network-test-smartcontracts-1 bash -c "python add_peer.py 8545 enode://c0c0e730...cb70@192.168.1.239:30303"
```
 
### Test Smart Contract from Device 2
 
```powershell
docker compose up test-smartcontracts -d
docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 0 8545"
```
 
**Expected output:**
```
contract_address:0x10626FA93259c3C0b6f609ebc354dEa734Cb6d9a
Current Message: Hello to you too from Node2!
Updating message... Tx Hash: 6b8d0f60...
Current Message: Hello to you too from Node2!
```
 
**This confirms:**
- Node2 can READ the smart contract deployed on Bootnode1
- Node2 can WRITE transactions to the blockchain
- The network is fully operational across two physical machines
 
---
## PHASE 3 — Adding Node3 on the Same Machine as Bootnode1
 
To run a third node on Device 1 alongside Bootnode1, you need three things to be different: **P2P port, RPC port, and data directory**. The `p2p-host` stays the same (same machine). Here's the logic:
 
| Setting | Bootnode1 | Node3 (same machine) | Node on Device 2 |
|---------|-----------|----------------------|-------------------|
| `p2p-host` | `192.168.1.239` | `192.168.1.239` (same) | `192.168.1.11` (its own IP) |
| `p2p-port` | `30303` (default) | `30304` (different) | `30303` (no conflict, different machine) |
| `rpc-http-port` | `8545` (default) | `8546` (different) | `8545` (no conflict, different machine) |
| `rpc-http-host` | `0.0.0.0` | `0.0.0.0` (same) | `0.0.0.0` (same) |
| `data-path` | `Node1/data/` | `Node3/data/` (different) | `Node2/data/` (different) |
| Docker `ports` | `30303:30303`, `8545:8545` | `30304:30304`, `8546:8546` | `30303:30303`, `8545:8545` |
 
### Step 3.1 — Create Node3 Directory
 
```powershell
cd C:\blockchain_tutorial\qbft\QBFT-Network
mkdir Node3\data
```
 
### Step 3.2 — Update docker-compose.yml
 
The Node3 service is already included in the Device 1 `docker-compose.yml`. Replace `<ENODE_URL>` in the `qbft-launch-node3` section with bootnode1's enode address from Step 1.7.
 
### Step 3.3 — Launch Node3
 
```powershell
docker compose up qbft-launch-node3
```
 
**Expected:** Node3 syncs blocks and shows `Peers: 1` (or `Peers: 2` if Node2 is also connected).
 
### Step 3.4 — Test Smart Contract from Node3
 
```powershell
docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 0 8546"
```
 
Note: the port is `8546` (Node3's RPC port), not `8545`.
 
### Adding Node4, Node5, etc.
 
Follow the same pattern — increment ports each time:
 
| Node | P2P Port | RPC Port | Docker ports mapping |
|------|----------|----------|----------------------|
| Bootnode1 | 30303 | 8545 | `30303:30303`, `8545:8545` |
| Node3 | 30304 | 8546 | `30304:30304`, `8546:8546` |
| Node4 | 30305 | 8547 | `30305:30305`, `8547:8547` |
| Node5 | 30306 | 8548 | `30306:30306`, `8548:8548` |
 
---
 