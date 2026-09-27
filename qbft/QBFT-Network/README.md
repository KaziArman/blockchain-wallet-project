## Genesis Configuration and Environment setup



File structure must be 
QBFT-Network/
├── qbftConfigFile.json
├── docker-compose.yml
├── clean.sh

After running ` docker compose up qbft-configure-genesis`. 
Output must look like:
```commandline
[+] Running 2/0
 ✔ Network qbft-network_default                     Created                                                                                                          0.0s 
 ✔ Container qbft-network-qbft-configure-genesis-1  Created                                                                                                          0.0s 
Attaching to qbft-configure-genesis-1./
qbft-configure-genesis-1  | 2025-03-18 01:38:17.314+00:00 | main | INFO  | GenerateBlockchainConfig | Generating 1 nodes keys.
qbft-configure-genesis-1  | 2025-03-18 01:38:17.317+00:00 | main | INFO  | GenerateBlockchainConfig | Generating keypair for node 0.
qbft-configure-genesis-1  | 2025-03-18 01:38:17.342+00:00 | main | INFO  | GenerateBlockchainConfig | Generating QBFT extra data.
qbft-configure-genesis-1  | 2025-03-18 01:38:17.343+00:00 | main | INFO  | GenerateBlockchainConfig | Writing genesis file.
qbft-configure-genesis-1 exited with code 0
```

You must get the following structure
QBFT-Network/
├── qbftConfigFile.json
├── docker-compose.yml
├── clean.sh
├── networkFiles
│     ├── data
│         ├── keys
│             ├── <public-key-file (like 0xf7224f3aae8f9e1d0d082dd5ecae992e916e9686)>

Now run ` docker compose up move-keys`, you will now get
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


Now run `docker compose up qbft-launch-bootnode1` to launch the blockchain node. You should observe an output that constantly mints blocks somewhat like this:
```commandline
....
qbft-launch-bootnode1-1  | 2025-03-20 03:05:48.491+00:00 | main | INFO  | FullSyncTargetManager | Unable to find sync target. Waiting for 1 peers minimum. Currently checking 0 peers for usefulness
qbft-launch-bootnode1-1  | 2025-03-20 03:05:48.492+00:00 | main | INFO  | Runner | Ethereum main loop is up.
qbft-launch-bootnode1-1  | 2025-03-20 03:05:48.529+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #174 / 0 tx / 0 pending / 0 (0.0%) gas / (0xeca9d3c22cb17023abb79315dfa4488f606f3f62db6123caef770b74cba3ab78)
qbft-launch-bootnode1-1  | 2025-03-20 03:05:50.010+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #175 / 0 tx / 0 pending / 0 (0.0%) gas / (0x25f694407cdf88f52e34d700685e56b879450fb0152c24488d051d14c09a27c9)
qbft-launch-bootnode1-1  | 2025-03-20 03:05:52.022+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #176 / 0 tx / 0 pending / 0 (0.0%) gas / (0x74a026ec45b896aaa3abda9cdba00b40694b2022ffccc84c678dcb912ab60968)
qbft-launch-bootnode1-1  | 2025-03-20 03:05:54.010+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #177 / 0 tx / 0 pending / 0 (0.0%) gas / (0x3c60d7ba40c385eab941dbef5cbc4e4509f8cf78c1c816f1fce8252704dcdd5a)
qbft-launch-bootnode1-1  | 2025-03-20 03:05:56.020+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #178 / 0 tx / 0 pending / 0 (0.0%) gas / (0x21cd2e71c130cbba019a4289c599767d4df591b3219599a0f480359e92e812ad)
qbft-launch-bootnode1-1  | 2025-03-20 03:05:58.020+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #179 / 0 tx / 0 pending / 0 (0.0%) gas / (0x2c95a339b98a6031c57a88d0d551b3e47a1037eb285417276fc6a454380e074f)
qbft-launch-bootnode1-1  | 2025-03-20 03:06:00.009+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #180 / 0 tx / 0 pending / 0 (0.0%) gas / (0x5b3fae260cdd5bd2437ad964400e2dc83f0083047ac863616c5703681a42b1b4)
qbft-launch-bootnode1-1  | 2025-03-20 03:06:02.022+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #181 / 0 tx / 0 pending / 0 (0.0%) gas / (0xda07d023842758a7ef2ff168593d7950d0106433c03b0675f2ee715539603833)
qbft-launch-bootnode1-1  | 2025-03-20 03:06:04.018+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #182 / 0 tx / 0 pending / 0 (0.0%) gas / (0x9bf9aad04a5a1470b6559a451aad71d4dde3a7ac50f58af1fe2900ff0b7abaa3)
qbft-launch-bootnode1-1  | 2025-03-20 03:06:06.010+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #183 / 0 tx / 0 pending / 0 (0.0%) gas / (0x80ef0149c57b3e7b14a35298a98c7a27683bfedbda02f72ba5aaa768f2b8af4e)
qbft-launch-bootnode1-1  | 2025-03-20 03:06:08.015+00:00 | BftProcessorExecutor-QBFT-0 | INFO  | QbftBesuControllerBuilder | Produced empty block #184 / 0 tx / 0 pending / 0 (0.0%) gas / (0xa073cb67047e1ee280c769fa32ce49bda803724bf08dc3fb5b492241e0df554b)
....
```


## To Test Smartcontract deployment
Run `docker compose up test-smartcontracts -d` to bring up a test container where all smartcontract tools have already been installed for you.
You can now run the command `docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 1 8545"` and you must see something like this:
```commandline
Compilation successful! ABI and Bytecode saved.
Deploying contract... Tx Hash: c4e9d650c2ce95c4f4ee0a9e52f469c56319f5f735dcb28969cfedfba60b9872
Contract deployed at: 0x10626FA93259c3C0b6f609ebc354dEa734Cb6d9a
Current Message: Hello, World!
Updating message... Tx Hash: 75ce38107ff6803b0b7604e7a1df633798d5527b61979bff15280af55f78f76b
Current Message: Hello to you too!
```

This means that you have been able to deploy a SmartContract on your blockchain using the bootnode.


## Creating and testing a Blockchain network

After you have launched bootnode1, go ahead and obtain its node address. The node address is a unique hexadeciman string that serves as an address of the blockchain node.
To obtain the node address, execute the following command:
`docker exec -it qbft-network-test-smartcontracts-1 bash -c "python find_enode_address.py localhost 8545"`

This should give you an output of:
```commandline
bootnode-address-1  | enode://1fb4c1a1b13b4cfe42dd610ccab692a216a5d332150dddf735113007df56413ff62f5832f5f8e8e7a496bc55f9a53d213578b1dfee373aa72540aecfa697c162@127.0.0.1:30303
```

Copy the enode address with the whole string starting (`enode://<string>@<ip>:<port>`) and paste it inside `docker-compose.yml` in the following location
```commandline
  qbft-launch-node2:
    image: hyperledger/besu:latest
    network_mode: "host"
    volumes:
      - .:/var/tmp/QBFT-Network
    working_dir: /var/tmp/QBFT-Network/Node2/
    command:
      - --data-path=/var/tmp/QBFT-Network/Node2/data/
      - --genesis-file=../networkFiles/genesis.json
      - --bootnodes=<PASTE_ENODE_ADDR_HERE>
      - --p2p-host=127.0.0.1
      - --p2p-port=30304
      - --rpc-http-port=8546
      - --rpc-http-enabled
      - --rpc-http-api=ETH,NET,QBFT,WEB3,ADMIN
      - --host-allowlist="*"
      - --rpc-http-cors-origins="all"
      - --profile=ENTERPRISE
```
Now run the command `docker compose up qbft-launch-node2` to bring up the second node.

You should observe the minting of new blocks as follows:
```commandline
....
qbft-launch-node2-1  | 2025-03-20 03:05:52.002+00:00 | nioEventLoopGroup-3-2 | INFO  | TransactionPoolFactory | Node out of sync, disabling transaction handling
qbft-launch-node2-1  | 2025-03-20 03:05:52.055+00:00 | nioEventLoopGroup-3-2 | INFO  | BlockPropagationManager | Saved announced block for future import 176 (0x74a026ec45b896aaa3abda9cdba00b40694b2022ffccc84c678dcb912ab60968) - 1 saved block(s)
qbft-launch-node2-1  | 2025-03-20 03:05:52.056+00:00 | nioEventLoopGroup-3-2 | INFO  | BlockPropagationManager | Retrieving parent 0x25f694407cdf88f52e34d700685e56b879450fb0152c24488d051d14c09a27c9 of block 176 (0x74a026ec45b896aaa3abda9cdba00b40694b2022ffccc84c678dcb912ab60968)
qbft-launch-node2-1  | 2025-03-20 03:05:52.094+00:00 | nioEventLoopGroup-3-2 | INFO  | BlockPropagationManager | Saved announced block for future import 175 (0x25f694407cdf88f52e34d700685e56b879450fb0152c24488d051d14c09a27c9) - 2 saved block(s)
qbft-launch-node2-1  | 2025-03-20 03:05:52.096+00:00 | nioEventLoopGroup-3-2 | INFO  | BlockPropagationManager | Retrieving parent 0xeca9d3c22cb17023abb79315dfa4488f606f3f62db6123caef770b74cba3ab78 of block 175 (0x25f694407cdf88f52e34d700685e56b879450fb0152c24488d051d14c09a27c9)
qbft-launch-node2-1  | 2025-03-20 03:05:52.107+00:00 | nioEventLoopGroup-3-2 | INFO  | BlockPropagationManager | Saved announced block for future import 174 (0xeca9d3c22cb17023abb79315dfa4488f606f3f62db6123caef770b74cba3ab78) - 3 saved block(s)
....
qbft-launch-node2-1  | 2025-03-20 03:05:52.184+00:00 | EthScheduler-Workers-0 | INFO  | TransactionPoolFactory | Node is in sync, enabling transaction handling
qbft-launch-node2-1  | 2025-03-20 03:05:52.187+00:00 | EthScheduler-Workers-0 | INFO  | PersistBlockTask | Imported empty block #170 / 0 tx / 0 om / 0 (0.0%) gas / (0x72d6b336a6f2fbf67f648e2246628a9803dab5ee75d6db2670af7e31bdecd4db) in 0.000s. Peers: 1
qbft-launch-node2-1  | 2025-03-20 03:05:52.188+00:00 | EthScheduler-Workers-0 | INFO  | BlockPropagationManager | Imported 1 pending blocks: [170]
qbft-launch-node2-1  | 2025-03-20 03:05:52.200+00:00 | EthScheduler-Workers-0 | INFO  | PersistBlockTask | Imported empty block #171 / 0 tx / 0 om / 0 (0.0%) gas / (0x4155db1552a77b5f479aba898fd34c3eeae8f41bde339e6f047042df138ee231) in 0.000s. Peers: 1
qbft-launch-node2-1  | 2025-03-20 03:05:52.200+00:00 | EthScheduler-Workers-0 | INFO  | BlockPropagationManager | Imported 1 pending blocks: [171]
qbft-launch-node2-1  | 2025-03-20 03:05:52.206+00:00 | EthScheduler-Workers-0 | INFO  | PersistBlockTask | Imported empty block #172 / 0 tx / 0 om / 0 (0.0%) gas / (0x4a4e01e90ad9fa589acfbf915a7d8311075e7cedc2861a5bcc5e0c85f63a29a6) in 0.000s. Peers: 1
qbft-launch-node2-1  | 2025-03-20 03:05:52.206+00:00 | EthScheduler-Workers-0 | INFO  | BlockPropagationManager | Imported 1 pending blocks: [172]
qbft-launch-node2-1  | 2025-03-20 03:05:52.207+00:00 | EthScheduler-Workers-0 | INFO  | PersistBlockTask | Block 172 (0x4a4e01e90ad9fa589acfbf915a7d8311075e7cedc2861a5bcc5e0c85f63a29a6) is already imported
qbft-launch-node2-1  | 2025-03-20 03:05:52.210+00:00 | EthScheduler-Workers-0 | INFO  | PersistBlockTask | Imported empty block #173 / 0 tx / 0 om / 0 (0.0%) gas / (0x40d02122dde85b5ebcfc1c9f85d9c01cccaba4a6c73a10077ab9cd44d78ef05b) in 0.000s. Peers: 1
....
```

To test that the SmartContract deployed earlier is visible to the new node, try to run the same code as before but with the first argument set to 0 and the second argument set to 8546, which is the RPC port of Node2 that you have just launched

`docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 0 8546"`

You should get an output like:
```commandline
contract_address:0x10626FA93259c3C0b6f609ebc354dEa734Cb6d9a
Current Message: Hello to you too!
Updating message... Tx Hash: 0540fb4e6cd408ebb001e9385f319bde2aa78793e104d4525ce1220624d0aa84
Current Message: Hello to you too!
```
Observe that the current message says "Hello to you too!" which is a message set when we deployed the contract on bootnode1. However, this was obtained by accessing the blockchain running on node 2 (listening on port 8546).

You can now keep adding more nodes such as node3, node4 and so on. A few of those configurations are provided in `docker-compose.yml`. All of them are the same except thy use different ports and have their own data directories to keep them distinct.

REMEMBER: All of them must have the same bootnode you have launched in the first step, else they wont be able to connect to the blockchain network and wont be able to access the deployed Smart Contracts.

### Deploying blockchain network across multiple computers

We can now extend our network across multiple computers by following the same logic as above. However, please keep in mind the following points:
- Bootnode has to be the same as bootnode1. Alternatively, they can also be one of the nodes spawned above (i.e. node2, node3 or node4 etc.). You would need to acquire the node address for each.
- The ports RPC-Port and P2P-Port must be free and available to use on the local machine.
- Extend the same `docker-compose.yml` file with the new configuration depending on which other computer you want to onboard.


Node address 0x750adabfbd90769a442a34a7a06ef97b01034dd1

Mohai Node: 0xe23bbd8eae00b0bd0e41bd5bde551a23d2e9c880

Lucius Node: 0xd1eaa261df19f8adad634dded3c5a4cb0eefbe4b

Boris Node: 0x2bfb17ce50b1fc3718c8c88f3ec98798fcd42b8b