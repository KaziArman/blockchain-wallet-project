
from solcx import compile_standard, install_solc
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys

SOL_FILE = "wallet.sol"
CONTRACT_NAME = "BasicWallet"

# Jay deploys the contract (he becomes the owner)
DEPLOYER = {
    "address": "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
    "private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63",
}


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8545"

    # Connect
    web3 = Web3(Web3.HTTPProvider(f"http://localhost:{port}"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert web3.is_connected(), "Cannot connect to node!"
    print(f"Connected to node on port {port}")

    # Compile
    with open(SOL_FILE, "r") as f:
        source = f.read()

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {SOL_FILE: {"content": source}},
            "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
        },
        solc_version="0.8.0",
    )

    with open("compiled_code.json", "w") as f:
        json.dump(compiled, f)

    abi = compiled["contracts"][SOL_FILE][CONTRACT_NAME]["abi"]
    bytecode = compiled["contracts"][SOL_FILE][CONTRACT_NAME]["evm"]["bytecode"]["object"]

    with open("abi.json", "w") as f:
        json.dump(abi, f)

    print("Compilation successful!")

    # Deploy
    addr = Web3.to_checksum_address(DEPLOYER["address"])
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor().build_transaction({
        "from": addr,
        "nonce": web3.eth.get_transaction_count(addr),
        "gasPrice": "0x0",
    })

    signed = web3.eth.account.sign_transaction(tx, DEPLOYER["private_key"])
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deploying... Tx: {tx_hash.hex()}")

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress
    print(f"Contract deployed at: {contract_address}")
    print(f"Owner: Jay ({addr})")

    with open("contract_address.json", "w") as f:
        json.dump({"contract_address": contract_address}, f)

    print("\nDone! You can now run: streamlit run app.py")


if __name__ == "__main__":
    main()