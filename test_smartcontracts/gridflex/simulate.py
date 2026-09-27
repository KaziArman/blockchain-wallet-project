from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys, time, secrets as sec_module, pickle, requests as req
from config import (
    ALL_ACCOUNTS, NODE_CONFIG, GRID_ADMIN, COMMITTEE_MEMBERS,
    IPFS_API, NORMAL_GRID_RATE, PEAK_GRID_RATE,
)
from matching import run_matching

ROLE_NAMES  = ["UTILITY", "PROSUMER", "CONSUMER", "FLEXIBLE", "INDUSTRIAL", "CRITICAL"]
TRADE_TYPES = {0: "P2P", 1: "GRID-DIST", 2: "FEED-IN"}


def connect(port):
    web3 = Web3(Web3.HTTPProvider(f"http://localhost:{port}"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert web3.is_connected(), f"Cannot connect to port {port}"
    return web3


def load_contract(web3):
    with open("abi.json") as f:
        abi = json.load(f)
    with open("contract_address.json") as f:
        addr = json.load(f)["contract_address"]
    return web3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)


def send_admin_tx(web3, func):
    addr = Web3.to_checksum_address(GRID_ADMIN["address"])
    tx = func.build_transaction({
        "from": addr, "nonce": web3.eth.get_transaction_count(addr), "gasPrice": 0, "gas": 3000000,
    })
    signed  = web3.eth.account.sign_transaction(tx, GRID_ADMIN["private_key"])
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex()


def push_to_ipfs(data_dict):
    try:
        serialized = pickle.dumps(data_dict)
        files = {'file': ('audit.pkl', serialized)}
        response = req.post(f"{IPFS_API}/add", files=files)
        if response.status_code == 200:
            return response.json()['Hash']
    except Exception as e:
        print(f"    IPFS push failed: {e}")
    return None



# SIMULATION SCENARIOS


SIMULATION = {
    1: {
        "desc":           "Sunny afternoon — homes compete in feed-in auction",
        "utility_supply": 5,
        "data": {
            "utility":   (0, 0, 0),
            "home01":    (8, 1, 5),   # surplus 7, bid 5c/kWh
            "home02":    (6, 1, 7),   # surplus 5, bid 7c/kWh
            "chemplant": (0, 5, 0),
            "school":    (0, 3, 0),
            "clinic":    (0, 2, 0),
        },
    },
    2: {
        "desc":           "Peak demand — shortage triggers 14c/kWh peak pricing",
        "utility_supply": 8,
        "data": {
            "utility":   (0, 0, 0),
            "home01":    (8, 1, 6),   # surplus 7, bid 6c
            "home02":    (6, 1, 8),   # surplus 5, bid 8c
            "chemplant": (0, 30, 0),
            "school":    (0, 8, 0),
            "clinic":    (0, 6, 0),
        },
    },
    3: {
        "desc":           "Cloudy day — no solar surplus, utility covers all",
        "utility_supply": 40,
        "data": {
            "utility":   (0, 0, 0),
            "home01":    (1, 4, 0),   # net consumer, no bid
            "home02":    (0, 3, 0),
            "chemplant": (0, 20, 0),
            "school":    (0, 6, 0),
            "clinic":    (0, 5, 0),
        },
    },
    4: {
        "desc":           "Evening — low demand, DR rewards for homes",
        "utility_supply": 25,
        "data": {
            "utility":   (0, 0, 0),
            "home01":    (0, 2, 0),   # consuming below baseline (3), earns DR
            "home02":    (0, 2, 0),   # consuming below baseline (3), earns DR
            "chemplant": (0, 8, 0),
            "school":    (0, 1, 0),
            "clinic":    (0, 4, 0),
        },
    },
    5: {
        "desc":           "Emergency heatwave — extreme shortage, peak pricing",
        "utility_supply": 10,
        "data": {
            "utility":   (0, 0, 0),
            "home01":    (3, 3, 0),   # self-sufficient, no surplus
            "home02":    (2, 2, 0),   # self-sufficient, no surplus
            "chemplant": (0, 25, 0),
            "school":    (0, 10, 0),
            "clinic":    (0, 8, 0),
        },
    },
}



# ROUND RUNNER


def run_round(web3, contract, sim_num, round_data):
    print(f"\n{'='*70}")
    print(f"  ROUND {sim_num}: {round_data['desc']}")
    print(f"{'='*70}")

    # Step 1: start round
    print(f"\n  Step 1: Utility declares {round_data['utility_supply']} kW capacity")
    send_admin_tx(web3, contract.functions.startRound(round_data["utility_supply"]))
    br = contract.functions.currentRound().call()
    print(f"    Blockchain round: #{br}")

    # Step 2: commitment hashes
    print(f"\n  Step 2: Nodes submit commitment hashes...")
    node_secrets = {}

    for key in COMMITTEE_MEMBERS:
        prod, cons, ask_price = round_data["data"][key]
        acct      = ALL_ACCOUNTS[key]
        node_addr = Web3.to_checksum_address(acct["address"])

        energy_secret = sec_module.token_hex(16)
        energy_hash   = contract.functions.generateCommitHash(prod, cons, energy_secret).call()
        send_admin_tx(web3, contract.functions.submitCommitmentFor(node_addr, energy_hash))

        bid_secret = None
        if ask_price > 0:
            bid_secret = sec_module.token_hex(16)
            bid_hash   = contract.functions.generateBidHash(ask_price, bid_secret).call()
            send_admin_tx(web3, contract.functions.submitBidCommitmentFor(node_addr, bid_hash))

        node_secrets[key] = {
            "energy_secret": energy_secret, "bid_secret": bid_secret,
            "ask_price": ask_price, "produced": prod, "consumed": cons,
        }

        bid_info = f"  + bid hash submitted" if ask_price > 0 else ""
        print(f"    {acct['name']:<25} energy hash: {energy_hash.hex()[:14]}...{bid_info}")

    # Step 3: off-chain matching
    print(f"\n  Step 3: Off-chain matching...")
    result_trades, fulfillments, dr_rewards, unserved, grid_rate, is_peak = run_matching(round_data)

    pricing_label = f"PEAK ({grid_rate}c/kWh)" if is_peak else f"NORMAL ({grid_rate}c/kWh)"
    print(f"    Grid pricing: {pricing_label}")

    # Step 4: post trade results — SEALED PRICES for feed-in
    print(f"\n  Step 4: Trade results on-chain (feed-in prices SEALED):")
    for t in result_trades:
        seller_addr = Web3.to_checksum_address(ALL_ACCOUNTS[t["seller"]]["address"])
        buyer_addr  = Web3.to_checksum_address(ALL_ACCOUNTS[t["buyer"]]["address"])

        if t["type"] == 2:
            # FEED-IN: post with price=0 (SEALED)
            send_admin_tx(web3, contract.functions.recordTrade(
                seller_addr, buyer_addr, t["amount"], 0, t["type"]
            ))
            # Record seller credits separately (total only, not per-unit)
            seller_credits = int(t["amount"] * t["price"])
            send_admin_tx(web3, contract.functions.recordSealedCredits(
                seller_addr, seller_credits
            ))
            # Utility pays (debit utility)
            utility_addr = Web3.to_checksum_address(ALL_ACCOUNTS["utility"]["address"])
            send_admin_tx(web3, contract.functions.recordSealedCredits(
                utility_addr, -seller_credits
            ))
            sname = ALL_ACCOUNTS[t["seller"]]["name"]
            bname = ALL_ACCOUNTS[t["buyer"]]["name"]
            print(f"    {sname:<25} -> {bname:<25}  {t['amount']:>3}kW  PRICE SEALED  [FEED-IN]")
            print(f"      Credits: +{seller_credits} (sealed, verify after bid reveal)")
        else:
            # GRID DISTRIBUTION: use public grid rate
            send_admin_tx(web3, contract.functions.recordTrade(
                seller_addr, buyer_addr, t["amount"], t["price"], t["type"]
            ))
            sname = ALL_ACCOUNTS[t["seller"]]["name"]
            bname = ALL_ACCOUNTS[t["buyer"]]["name"]
            print(f"    {sname:<25} -> {bname:<25}  {t['amount']:>3}kW  at {t['price']}c/kWh  [GRID-DIST]")

    # Step 5: fulfillment
    print(f"\n  Step 5: Fulfillment percentages:")
    for key, ful in fulfillments.items():
        node_addr = Web3.to_checksum_address(ALL_ACCOUNTS[key]["address"])
        send_admin_tx(web3, contract.functions.recordFulfillment(
            node_addr, ful["percent"], ful["is_producer"]
        ))
        label = "Seller" if ful["is_producer"] else "Consumer"
        print(f"    {ALL_ACCOUNTS[key]['name']:<25}  {ful['percent']:>3}%  ({label})")

    # Step 6: demand response
    if dr_rewards:
        print(f"\n  Step 6: Demand response:")
        for key, reduced in dr_rewards.items():
            node_addr = Web3.to_checksum_address(ALL_ACCOUNTS[key]["address"])
            send_admin_tx(web3, contract.functions.recordDemandResponse(node_addr, reduced))
            print(f"    {ALL_ACCOUNTS[key]['name']:<25}  -{reduced}kW vs baseline  -> {reduced*5} tokens")

    # Step 7: settle
    send_admin_tx(web3, contract.functions.settleRound(unserved))

    # Step 8: record pricing
    send_admin_tx(web3, contract.functions.setRoundPricing(br, is_peak, grid_rate))

    # Step 9: IPFS audit
    print(f"\n  Step 8: IPFS audit trail...")
    audit = {
        "round": br, "description": round_data["desc"],
        "utility_supply": round_data["utility_supply"],
        "grid_rate": grid_rate, "is_peak": is_peak,
        "trades": result_trades, "fulfillments": fulfillments,
        "dr_rewards": dr_rewards, "unserved": unserved,
    }
    cid = push_to_ipfs(audit)
    if cid:
        send_admin_tx(web3, contract.functions.setRoundAuditCID(br, cid))
        print(f"    Audit CID: {cid}")
    else:
        print(f"    IPFS not available — skipped")

    # Summary
    rd = contract.functions.getRoundData(br).call()
    print(f"\n  Summary (round #{br}):")
    print(f"    Feed-in:   {rd[3]:>3} kW (prices SEALED)")
    print(f"    Grid dist: {rd[2]:>3} kW (at {grid_rate}c/kWh {'PEAK' if is_peak else 'normal'})")
    print(f"    Unserved:  {rd[5]:>3} kW")
    print(f"    Trades:    {rd[6]:>3}")

    return br, node_secrets



# BID REVEAL DEMO


def demo_reveal(web3, contract, blockchain_round, node_secrets):
    print(f"\n{'='*70}")
    print(f"  BID REVEAL — Round #{blockchain_round}")
    print(f"  Sellers prove their sealed bid was honest")
    print(f"{'='*70}")

    sellers = {k: s for k, s in node_secrets.items() if s.get("bid_secret")}
    if not sellers:
        print("  No sealed bids this round.")
        return

    for key, s in sellers.items():
        acct      = ALL_ACCOUNTS[key]
        node_addr = Web3.to_checksum_address(acct["address"])

        print(f"\n  {acct['name']} reveals bid: {s['ask_price']}c/kWh")

        tx = contract.functions.revealBid(
            blockchain_round, s["ask_price"], s["bid_secret"]
        ).build_transaction({
            "from": node_addr,
            "nonce": web3.eth.get_transaction_count(node_addr),
            "gasPrice": 0,
        })
        signed  = web3.eth.account.sign_transaction(tx, acct["private_key"])
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        revealed = contract.functions.hasBidRevealed(blockchain_round, node_addr).call()
        price    = contract.functions.revealedBidPrice(blockchain_round, node_addr).call()
        print(f"    Verified: {'YES' if revealed else 'FAILED'}  |  Now public: {price}c/kWh")
        print(f"    Anyone can verify: {price}c × {s['produced']-s['consumed']}kW = "
              f"{price * (s['produced']-s['consumed'])} credits earned")



# FINAL SUMMARY


def print_summary(web3, contract, first_br, last_br):
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY (rounds #{first_br}–#{last_br})")
    print(f"{'='*70}")

    nc = contract.functions.nodeCount().call()
    print(f"\n  {'Name':<25} {'Role':<12} {'Tokens':>8} {'Credits':>10}")
    print(f"  {'-'*25} {'-'*12} {'-'*8} {'-'*10}")
    for i in range(nc):
        addr = contract.functions.getNodeAddress(i).call()
        info = contract.functions.getNodeInfo(addr).call()
        cs = f"+{info[4]}" if info[4] >= 0 else str(info[4])
        print(f"  {info[0]:<25} {ROLE_NAMES[info[1]]:<12} {info[3]:>8} {cs:>10}")

    print(f"\n  Per-round:")
    for br in range(first_br, last_br + 1):
        rd      = contract.functions.getRoundData(br).call()
        is_peak = contract.functions.isPeakRound(br).call()
        rate    = contract.functions.roundGridRate(br).call()
        audit   = contract.functions.roundAuditCID(br).call()
        p_str   = f"PEAK@{rate}c" if is_peak else f"@{rate}c"
        i_str   = f"IPFS:{audit[:12]}..." if audit else "(no IPFS)"
        print(f"    #{br}: FeedIn={rd[3]}kW Grid={rd[2]}kW DR={rd[4]}kW Unserved={rd[5]}kW {p_str} {i_str}")

    print(f"\n  Privacy summary:")
    print(f"    ON-CHAIN:  trades (feed-in prices SEALED), fulfillment %, DR tokens, audit CIDs")
    print(f"    SEALED:    feed-in bid prices (revealed only when seller chooses)")
    print(f"    OFF-CHAIN: individual production, consumption, capacity data")



# MAIN


def main():
    port     = sys.argv[1] if len(sys.argv) > 1 else "8545"
    web3     = connect(port)
    contract = load_contract(web3)

    print("GridFlex Chain v3 — Sealed Bid Price Simulation")
    print(f"Contract: {contract.address}")
    print(f"Features: sealed feed-in prices, dynamic pricing, IPFS audit")

    all_secrets       = {}
    blockchain_rounds = {}

    for sim_num in range(1, 6):
        br, secrets_r = run_round(web3, contract, sim_num, SIMULATION[sim_num])
        all_secrets[br]            = secrets_r
        blockchain_rounds[sim_num] = br
        time.sleep(1)

    first_br = blockchain_rounds[1]
    last_br  = blockchain_rounds[5]

    print_summary(web3, contract, first_br, last_br)

    # Reveal bids for rounds that had feed-in auctions
    for sim_num in [1, 2]:
        br = blockchain_rounds[sim_num]
        demo_reveal(web3, contract, br, all_secrets[br])

    print(f"\n{'='*70}")
    print(f"  Simulation complete!")
    print(f"  Feed-in prices were SEALED during trading.")
    print(f"  Sellers revealed their bids AFTER settlement.")
    print(f"  Grid distribution used public rate (12c normal, 14c peak).")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
