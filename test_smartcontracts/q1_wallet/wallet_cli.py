"""
BasicWallet CLI — Terminal commands for smart contract operations

Usage examples:

  # Check Phil's balance
  python wallet_cli.py balance Phil 8545

  # Phil deposits 10 ETH
  python wallet_cli.py deposit Phil 10 8545

  # Phil deposits 10 more ETH (just run the same command again)
  python wallet_cli.py deposit Phil 10 8545

  # Jay withdraws 20% from all depositors
  python wallet_cli.py withdraw-all Jay 20 8545

  # Jay withdraws 50% from Phil only
  python wallet_cli.py withdraw-one Jay Phil 50 8545

  # Phil tries to withdraw (will fail — proves access control)
  python wallet_cli.py withdraw-all Phil 10 8545

  # Check everyone's balance
  python wallet_cli.py balances 8545

  # Show contract info (owner, total held, depositor count)
  python wallet_cli.py info 8545

Arguments:
  Last argument is always the RPC port (8545 for bootnode1, 8546 for node3, etc.)
"""

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys

# ACCOUNTS — each person's identity


ACCOUNTS = {
    "Jay": {
        "address": "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
        "private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63",
    },
    "Phil": {
        "address": "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
        "private_key": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3",
    },
    "Cam": {
        "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
        "private_key": "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f",
    },
        "Kazi": {
        "address": "0xC3d816631b731783686C670020C2bf0C99DA5698",
        "private_key": "0xe14b727a6ba13a5515d5c818c4f886d89c790989de708b1272e8c623ae4ead0d",
    },
}


def connect(port):
    """Connect to the blockchain node."""
    web3 = Web3(Web3.HTTPProvider(f"http://localhost:{port}"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert web3.is_connected(), f"Cannot connect to node on port {port}!"
    return web3


def load_contract(web3):
    """Load the deployed contract."""
    with open("abi.json", "r") as f:
        abi = json.load(f)
    with open("contract_address.json", "r") as f:
        addr = json.load(f)["contract_address"]
    return web3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)


def send_tx(web3, contract_func, who, value_wei=0):
    """Sign and send a transaction as a specific person."""
    acct = ACCOUNTS[who]
    addr = Web3.to_checksum_address(acct["address"])
    key = acct["private_key"]

    tx = contract_func.build_transaction({
        "from": addr,
        "nonce": web3.eth.get_transaction_count(addr),
        "gasPrice": "0x0",
        "value": value_wei,
    })

    signed = web3.eth.account.sign_transaction(tx, key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt


def to_ether(wei):
    return float(Web3.from_wei(wei, "ether"))


def shorten(addr):
    return f"{addr[:8]}...{addr[-6:]}"


# COMMANDS

def cmd_balance(web3, contract, args):
    """Check one person's balance.
    Usage: python wallet_cli.py balance Phil 8545
    """
    who = args[0]
    if who not in ACCOUNTS:
        print(f"Unknown account: {who}. Known accounts: {list(ACCOUNTS.keys())}")
        return

    addr = Web3.to_checksum_address(ACCOUNTS[who]["address"])
    wallet_bal = contract.functions.getBalance(addr).call()
    chain_bal = web3.eth.get_balance(addr)

    print(f"\n  {who}'s balances:")
    print(f"  In wallet contract: {to_ether(wallet_bal):.4f} ETH")
    print(f"  On-chain ETH:       {to_ether(chain_bal):.4f} ETH")
    print(f"  Address:            {addr}")


def cmd_balances(web3, contract, args):
    """Check ALL depositors' balances.
    Usage: python wallet_cli.py balances 8545
    """
    count = contract.functions.getDepositorCount().call()

    if count == 0:
        print("\n  No depositors yet.")
        return

    print(f"\n  All depositor balances ({count} depositors):")
    print(f"  {'Name':<10} {'Address':<20} {'Balance':>15}")
    print(f"  {'-'*10} {'-'*20} {'-'*15}")

    for i in range(count):
        dep_addr = contract.functions.getDepositor(i).call()
        bal = contract.functions.getBalance(dep_addr).call()

        # Find name
        name = "Unknown"
        for n, a in ACCOUNTS.items():
            if Web3.to_checksum_address(a["address"]).lower() == dep_addr.lower():
                name = n
                break

        print(f"  {name:<10} {shorten(dep_addr):<20} {to_ether(bal):>12.4f} ETH")

    total = contract.functions.getContractBalance().call()
    print(f"\n  Contract total: {to_ether(total):.4f} ETH")


def cmd_deposit(web3, contract, args):
    """Deposit ETH into the wallet.
    Usage: python wallet_cli.py deposit Phil 10 8545
    """
    who = args[0]
    amount = float(args[1])

    if who not in ACCOUNTS:
        print(f"Unknown account: {who}. Known accounts: {list(ACCOUNTS.keys())}")
        return

    addr = Web3.to_checksum_address(ACCOUNTS[who]["address"])

    # Show balance before
    bal_before = contract.functions.getBalance(addr).call()
    print(f"\n  {who}'s balance before: {to_ether(bal_before):.4f} ETH")

    # Deposit
    wei = Web3.to_wei(amount, "ether")
    print(f"  Depositing {amount} ETH as {who}...")
    tx_hash, receipt = send_tx(web3, contract.functions.deposit(), who, value_wei=wei)

    # Show balance after
    bal_after = contract.functions.getBalance(addr).call()
    print(f"  {who}'s balance after:  {to_ether(bal_after):.4f} ETH")
    print(f"  Tx hash: {tx_hash}")
    print(f"  Block: #{receipt.blockNumber}")
    print(f"  Status: {'Success' if receipt.status == 1 else 'FAILED'}")


def cmd_withdraw_all(web3, contract, args):
    """Owner withdraws x% from ALL depositors.
    Usage: python wallet_cli.py withdraw-all Jay 20 8545
    """
    who = args[0]
    pct = int(args[1])

    if who not in ACCOUNTS:
        print(f"Unknown account: {who}.")
        return

    addr = Web3.to_checksum_address(ACCOUNTS[who]["address"])
    owner = contract.functions.owner().call()

    print(f"\n  Caller: {who} ({shorten(addr)})")
    print(f"  Owner:  {shorten(owner)}")
    print(f"  Match:  {'YES' if addr.lower() == owner.lower() else 'NO'}")

    eth_before = web3.eth.get_balance(addr)
    print(f"\n  {who}'s ETH before: {to_ether(eth_before):.4f}")

    print(f"  Calling withdrawFromAll({pct}%)...")
    try:
        tx_hash, receipt = send_tx(web3, contract.functions.withdrawFromAll(pct), who)
        eth_after = web3.eth.get_balance(addr)

        print(f"  SUCCESS!")
        print(f"  {who}'s ETH after:  {to_ether(eth_after):.4f}")
        print(f"  {who} received:     {to_ether(eth_after - eth_before):.4f} ETH")
        print(f"  Tx hash: {tx_hash}")
        print(f"  Block: #{receipt.blockNumber}")
    except Exception as e:
        print(f"  FAILED! Transaction reverted.")
        print(f"  Reason: Only the owner can withdraw.")
        print(f"  {who} is NOT the owner — the contract rejected this transaction.")


def cmd_withdraw_one(web3, contract, args):
    """Owner withdraws x% from ONE specific depositor.
    Usage: python wallet_cli.py withdraw-one Jay Phil 50 8545
    """
    who = args[0]
    target_name = args[1]
    pct = int(args[2])

    if who not in ACCOUNTS or target_name not in ACCOUNTS:
        print(f"Unknown account. Known: {list(ACCOUNTS.keys())}")
        return

    target_addr = Web3.to_checksum_address(ACCOUNTS[target_name]["address"])
    bal_before = contract.functions.getBalance(target_addr).call()

    print(f"\n  {who} withdrawing {pct}% from {target_name}...")
    print(f"  {target_name}'s balance before: {to_ether(bal_before):.4f} ETH")

    try:
        tx_hash, receipt = send_tx(
            web3,
            contract.functions.withdrawFromDepositor(target_addr, pct),
            who
        )
        bal_after = contract.functions.getBalance(target_addr).call()
        print(f"  {target_name}'s balance after:  {to_ether(bal_after):.4f} ETH")
        print(f"  Taken: {to_ether(bal_before - bal_after):.4f} ETH")
        print(f"  Tx hash: {tx_hash}")
        print(f"  Status: Success")
    except Exception as e:
        print(f"  FAILED! {who} is not the owner.")


def cmd_info(web3, contract, args):
    """Show contract info.
    Usage: python wallet_cli.py info 8545
    """
    owner = contract.functions.owner().call()
    total = contract.functions.getContractBalance().call()
    count = contract.functions.getDepositorCount().call()

    # Find owner name
    owner_name = "Unknown"
    for n, a in ACCOUNTS.items():
        if Web3.to_checksum_address(a["address"]).lower() == owner.lower():
            owner_name = n
            break

    print(f"\n  Contract address:  {contract.address}")
    print(f"  Owner:             {owner_name} ({shorten(owner)})")
    print(f"  Total ETH held:    {to_ether(total):.4f} ETH")
    print(f"  Depositor count:   {count}")
    print(f"  Latest block:      #{web3.eth.block_number}")


# MAIN

COMMANDS = {
    "balance": cmd_balance,
    "balances": cmd_balances,
    "deposit": cmd_deposit,
    "withdraw-all": cmd_withdraw_all,
    "withdraw-one": cmd_withdraw_one,
    "info": cmd_info,
}

USAGE = """
BasicWallet CLI — Terminal commands for smart contract operations

Commands:
  python wallet_cli.py balance Phil 8545              Check Phil's balance
  python wallet_cli.py balances 8545                  Check ALL balances
  python wallet_cli.py deposit Phil 10 8545           Phil deposits 10 ETH
  python wallet_cli.py deposit Phil 10 8545           Phil deposits 10 MORE (run again)
  python wallet_cli.py withdraw-all Jay 20 8545       Jay withdraws 20% from everyone
  python wallet_cli.py withdraw-one Jay Phil 50 8545  Jay withdraws 50% from Phil
  python wallet_cli.py withdraw-all Phil 10 8545      Phil tries to withdraw (FAILS)
  python wallet_cli.py info 8545                      Show contract info

The last argument is always the RPC port:
  8545 = bootnode1 (Device 1)
  8546 = node3 (Device 1, same machine)
  8545 = node2 (Device 2, different machine)
"""

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print(USAGE)
        sys.exit(0)

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print(USAGE)
        sys.exit(1)

    # Port is always the last argument
    port = sys.argv[-1]
    # Args are everything between command and port
    args = sys.argv[2:-1]

    web3 = connect(port)
    contract = load_contract(web3)
    COMMANDS[command](web3, contract, args)
