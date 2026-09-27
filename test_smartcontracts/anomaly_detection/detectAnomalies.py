from solcx import compile_standard, install_solc
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_keyfile import extract_key_from_keyfile
import json, os, sys

#dummy code to simulate statistics
def pSigmaI(alpha, sigma_i, P_sigma_cap):
    beta = 1 / float(100)
    if sigma_i == 0:
        a_i = (1 - alpha) * P_sigma_cap[0]
        b_i = (1 - beta) * P_sigma_cap[1]
    else:
        a_i = (alpha) * P_sigma_cap[0]
        b_i = (beta) * P_sigma_cap[1]

    return a_i, b_i, (a_i + b_i)


def updatePrior(a_i, b_i):
    P_sigma_cap0 = float(a_i) / (a_i + b_i)
    P_sigma_cap1 = float(b_i) / (a_i + b_i)
    return P_sigma_cap0, P_sigma_cap1

def get_private_key(password,keystore_path):
    private_key = extract_key_from_keyfile(keystore_path, password.encode())

    print("Private Key:", private_key.hex())
    return private_key.hex()

def compile_smart_contract(filename):
    # Read the Solidity contract
    with open(filename, "r") as file:
        contract_content = file.read()

    # Compile the contract
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {filename: {"content": contract_content}},
            "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
        },
        solc_version="0.8.0",
    )

    # Save compiled output
    with open("compiled_code.json", "w") as file:
        json.dump(compiled_sol, file)

    # Extract ABI & Bytecode
    abi = compiled_sol["contracts"]["detectAnomalies.sol"]["GlobalAttackDetector"]["abi"]
    bytecode = compiled_sol["contracts"]["detectAnomalies.sol"]["GlobalAttackDetector"]["evm"]["bytecode"]["object"]

    # Save ABI to a file
    with open("abi.json", "w") as file:
        json.dump(abi, file)

    print("Compilation successful! ABI and Bytecode saved.")

def deploy_contract(private_key,public_key,web3):

    PRIVATE_KEY = private_key  # Your private key
    ACCOUNT_ADDRESS = public_key  # Your Ethereum PK address
    assert web3.is_connected(), "Web3 is not connected!"

    # Load ABI & Bytecode
    with open("abi.json", "r") as file:
        abi = json.load(file)

    with open("compiled_code.json", "r") as file:
        compiled_sol = json.load(file)

    bytecode = compiled_sol["contracts"]["detectAnomalies.sol"]["GlobalAttackDetector"]["evm"]["bytecode"]["object"]

    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    # Create transaction
    tx = contract.constructor().build_transaction({
        'from': ACCOUNT_ADDRESS,
        'nonce': web3.eth.get_transaction_count(ACCOUNT_ADDRESS),
        'gasPrice': "0x0",
    })

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"Deploying contract... Tx Hash: {tx_hash.hex()}")
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Contract deployed at: {tx_receipt.contractAddress}")
    return tx_receipt.contractAddress

# Read the message
def setData(contract,bi0ai,ai0psi,sigmai,rank,PUBLIC_KEY,PRIVATE_KEY):
    tx = contract.functions.setData(int(bi0ai), int(ai0psi), int(sigmai), int(rank)).build_transaction({
        'from': PUBLIC_KEY,
        'nonce': web3.eth.get_transaction_count(PUBLIC_KEY),
        'gasPrice': "0x0"
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Updating message... Tx Hash: {tx_hash.hex()}")
    web3.eth.wait_for_transaction_receipt(tx_hash)

# Update the message
def computeProbability(contract,D):
    retval = contract.functions.getGlobalAttackProbability().call()
    P = float(retval[1]/D)*(1+float(retval[0])/D)
    print(f"Current probability: {P}")

D=1e4

if __name__ == "__main__":

    contract_compile_deploy = int(sys.argv[1])
    node_port = sys.argv[2]

    node_ip="localhost"

    private_key = "0x74d507033d2c0f22b34c42ea1bf2d4f86c7f2061e19984a824d95603641a2907"  # new_local_account.address
    public_key = Web3.to_checksum_address(
        "0x94b7c73603c2468e23fc83f9d9aa25981ae4e193")  # web3.to_hex(new_local_account.key)

    # Connect to Ethereum network (local or testnet)
    HTTP_URL = f"http://{node_ip}:{node_port}"
    web3 = Web3(Web3.HTTPProvider(HTTP_URL))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if contract_compile_deploy:

        compile_smart_contract("detectAnomalies.sol")

        new_local_account = web3.eth.account.create()

        contract_address = deploy_contract(private_key,public_key,web3)

        with open("contract_address.json","w") as contract_write_file:
            json.dump({"contract_address":contract_address},contract_write_file)

    # Load ABI
    with open("abi.json", "r") as file:
        abi = json.load(file)

    with open("contract_address.json","r") as contract_file:
        contract_address = json.load(contract_file).get("contract_address","")

    print(f"contract_address:{contract_address}")

    # # Connect to contract
    contract = web3.eth.contract(address=contract_address, abi=abi)


    for t in range(10):

        #parameters for computing probability of alarms
        a_i, b_i, P_sigma_i = pSigmaI(0.05, 1, [0.2,0.8])
        bi0ai = float(b_i) * D / a_i
        ai0psi = (float(a_i) / P_sigma_i) * D
        psi = P_sigma_i * D
        sigmai = 1

        # Compute global state
        setData(contract,bi0ai,ai0psi,sigmai,rank=0,PUBLIC_KEY=public_key,PRIVATE_KEY=private_key)

        computeProbability(contract,D)

        p0,p1 = updatePrior(a_i, b_i)
