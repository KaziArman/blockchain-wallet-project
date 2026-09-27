from solcx import compile_standard, install_solc
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys, time
from config import ALL_ACCOUNTS, NODE_CONFIG, GRID_ADMIN, COMMITTEE_SIZE

SOL_FILE      = "gridflex.sol"
CONTRACT_NAME = "GridFlexChain"
ROLE_NAMES    = ["UTILITY", "PROSUMER", "CONSUMER", "FLEXIBLE", "INDUSTRIAL", "CRITICAL"]
PRIO_NAMES    = ["NORMAL", "HIGH", "HIGHEST"]


def send_tx(web3, func, from_addr, key):
    """
    Builds, signs, and sends a transaction, then explicitly waits for the 
    receipt to ensure the nonce increments correctly for the next call.
    """
    tx = func.build_transaction({
        "from":     from_addr,
        "nonce":    web3.eth.get_transaction_count(from_addr),
        "gasPrice": 0,
        "gas":      3000000,
    })
    signed  = web3.eth.account.sign_transaction(tx, key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    
    # Wait for the receipt before returning to ensure sequential processing
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8545"
    web3 = Web3(Web3.HTTPProvider(f"http://localhost:{port}"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert web3.is_connected(), f"Cannot connect to port {port}"
    print(f"Connected to port {port}  |  Chain ID: {web3.eth.chain_id}\n")

    # ---- Compile ----
    print("Compiling gridflex.sol ...")
    install_solc("0.8.0")

    with open(SOL_FILE, "r") as f:
        source = f.read()

    compiled = compile_standard({
        "language": "Solidity",
        "sources":  {SOL_FILE: {"content": source}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
    }, solc_version="0.8.0")

    abi      = compiled["contracts"][SOL_FILE][CONTRACT_NAME]["abi"]
    bytecode = compiled["contracts"][SOL_FILE][CONTRACT_NAME]["evm"]["bytecode"]["object"]

    with open("abi.json", "w") as f:
        json.dump(abi, f, indent=2)

    print("Compilation OK → abi.json\n")

    # ---- Deploy ----
    admin_addr = Web3.to_checksum_address(GRID_ADMIN["address"])
    admin_key  = GRID_ADMIN["private_key"]

    print("Deploying contract...")
    factory = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx = factory.constructor().build_transaction({
        "from":     admin_addr,
        "nonce":    web3.eth.get_transaction_count(admin_addr),
        "gasPrice": 0,
        "gas":      15000000,
    })
    signed  = web3.eth.account.sign_transaction(tx, admin_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = receipt.contractAddress
    
    # FIX 1: Verify code presence before proceeding
    code = web3.eth.get_code(contract_address)
    if len(code) == 0:
        print(f"FATAL: Contract deployed at {contract_address} but code is 0 bytes.")
        print("Check if the QBFT validators are sealing blocks.")
        sys.exit(1)
    
    print(f"Contract deployed at: {contract_address} ({len(code)} bytes verified)\n")

    with open("contract_address.json", "w") as f:
        json.dump({"contract_address": contract_address}, f)

    deployed = web3.eth.contract(address=contract_address, abi=abi)

    # ---- Register 6 nodes ----
    registration_order = ["utility", "home01", "home02", "chemplant", "school", "clinic"]

    print("Registering nodes:")
    for key in registration_order:
        acct   = ALL_ACCOUNTS[key]
        config = NODE_CONFIG[key]
        addr   = Web3.to_checksum_address(acct["address"])

        send_tx(
            web3,
            deployed.functions.registerNode(addr, acct["name"], config["role"], config["priority"]),
            admin_addr, admin_key,
        )
        print(f"  {acct['name']:<30}  role={ROLE_NAMES[config['role']]:<12}  addr={addr[:10]}...")

    # ---- Set committee size ----
    send_tx(web3, deployed.functions.setCommitteeSize(COMMITTEE_SIZE), admin_addr, admin_key)
    print(f"\nCommittee size set to {COMMITTEE_SIZE}")

    # QBFT state finalization can lag slightly behind transaction receipts.
    print("\nWaiting 3 seconds for state synchronization...")
    time.sleep(3)

    # ---- Verify ----
    try:
        nc = deployed.functions.nodeCount().call()
        cs = deployed.functions.committeeSize().call()
        print(f"\nVerification Success:")
        print(f"  Nodes registered : {nc}")
        print(f"  Committee size   : {cs}")
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        print("The contract exists, but the node is not returning data yet. Try calling verification again in a moment.")

    print(f"\nNext step: 1. Run python simulate.py {port}, or 2. Run 'docker compose up app-ui --remove-orphans' to start the streamlit UI.")


if __name__ == "__main__":
    main()
