import json
import os
import sys
import secrets as sec_module
import streamlit as st
from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from config import (
    ALL_ACCOUNTS, NODE_CONFIG, GRID_ADMIN, WHITELIST,
    PARTICIPANT_NAMES, COMMITTEE_SIZE, key_for_address,
)
from matching import run_matching

# CLI port arg
port = "8545"
for i, arg in enumerate(sys.argv):
    if arg == "--port" and i + 1 < len(sys.argv):
        port = sys.argv[i + 1]
NODE_URL = os.environ.get("NODE_URL", f"http://localhost:{port}")

ROLE_NAMES  = ["UTILITY", "PROSUMER", "CONSUMER", "FLEXIBLE", "INDUSTRIAL", "CRITICAL"]
PRIO_NAMES  = ["NORMAL", "HIGH", "HIGHEST"]
TRADE_TYPES = {1: "Grid Distribution", 2: "Feed-in Auction"}

BIDS_FILE_TEMPLATE = "round_{}_bids.json"

# Page config
st.set_page_config(
    page_title="GridFlex Chain",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Space Mono', monospace !important; }
.phase-banner {
    padding: 14px 20px; border-radius: 10px;
    font-family: 'Space Mono', monospace; font-size: 0.85rem;
    text-align: center; margin-bottom: 18px;
}
.phase-commit   { background:#0f2817; border:1px solid #22c55e; color:#86efac; }
.phase-waiting  { background:#172554; border:1px solid #3b82f6; color:#93c5fd; }
.phase-ready    { background:#451a03; border:1px solid #f59e0b; color:#fcd34d; }
.phase-results  { background:#1e1b4b; border:1px solid #a78bfa; color:#c4b5fd; }
.phase-idle     { background:#1c1917; border:1px solid #57534e; color:#a8a29e; }
.addr-chip {
    font-family: 'Space Mono', monospace; font-size: 0.78rem;
    background: #1e293b; border: 1px solid #334155;
    padding: 3px 10px; border-radius: 6px; color: #94a3b8;
    display: inline-block; word-break: break-all;
}
.node-header {
    font-family: 'Space Mono', monospace;
    color: #e2e8f0; font-weight: 700; margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# Blockchain helpers
@st.cache_resource
def get_web3():
    w3 = Web3(Web3.HTTPProvider(NODE_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


@st.cache_resource
def get_contract(_web3):
    try:
        with open("abi.json") as f:
            abi = json.load(f)
        with open("contract_address.json") as f:
            addr = json.load(f)["contract_address"]
        return _web3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
    except FileNotFoundError:
        return None


def send_tx(web3, fn, sender_addr, private_key):
    tx = fn.build_transaction({
        "from":     sender_addr,
        "nonce":    web3.eth.get_transaction_count(sender_addr),
        "gasPrice": 0,
    })
    signed  = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)


def send_admin_tx(web3, fn):
    addr = Web3.to_checksum_address(GRID_ADMIN["address"])
    tx = fn.build_transaction({
        "from": addr, "nonce": web3.eth.get_transaction_count(addr), "gasPrice": 0,
    })
    signed  = web3.eth.account.sign_transaction(tx, GRID_ADMIN["private_key"])
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    web3.eth.wait_for_transaction_receipt(tx_hash)


# Phase detection

def get_phase(contract, user_address):
    cr = contract.functions.currentRound().call()
    if cr == 0:
        return "IDLE", cr

    rd = contract.functions.getRoundData(cr).call()
    if rd[7]:
        return "RESULTS", cr

    if contract.functions.allCommitted().call():
        return "READY", cr

    if contract.functions.hasCommitted(cr, user_address).call():
        return "WAITING", cr

    return "COMMIT", cr


# Bids local file (simulates ISO secure channel)

def save_bid(round_num, node_key, produced, consumed, ask_price,
             address, energy_secret, bid_secret):
    fname = BIDS_FILE_TEMPLATE.format(round_num)
    try:
        with open(fname) as f:
            bids = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        bids = {}
    bids[node_key] = {
        "produced": produced, "consumed": consumed,
        "ask_price": ask_price, "address": address,
        "energy_secret": energy_secret, "bid_secret": bid_secret,
    }
    with open(fname, "w") as f:
        json.dump(bids, f, indent=2)


def load_bids(round_num):
    fname = BIDS_FILE_TEMPLATE.format(round_num)
    try:
        with open(fname) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def bids_to_round_data(bids, utility_supply):
    data = {"utility": (0, 0, 0)}
    for key, b in bids.items():
        data[key] = (b["produced"], b["consumed"], b["ask_price"])
    return {"utility_supply": utility_supply, "data": data}


# Process round (auto-triggered when all submit, or manual by utility)

def process_round(web3, contract, round_num, utility_supply):
    bids = load_bids(round_num)
    if not bids:
        st.error("No bid data found. Cannot process round.")
        return False

    round_data = bids_to_round_data(bids, utility_supply)
    result_trades, fulfillments, dr_rewards, unserved, grid_rate, is_peak = run_matching(round_data)

    for t in result_trades:
        seller_addr = Web3.to_checksum_address(ALL_ACCOUNTS[t["seller"]]["address"])
        buyer_addr  = Web3.to_checksum_address(ALL_ACCOUNTS[t["buyer"]]["address"])

        if t["type"] == 2:
            # FEED-IN: sealed price (post 0), credits recorded separately
            send_admin_tx(web3, contract.functions.recordTrade(
                seller_addr, buyer_addr, t["amount"], 0, t["type"]
            ))
            seller_credits = int(t["amount"] * t["price"])
            send_admin_tx(web3, contract.functions.recordSealedCredits(
                seller_addr, seller_credits
            ))
            utility_addr = Web3.to_checksum_address(ALL_ACCOUNTS["utility"]["address"])
            send_admin_tx(web3, contract.functions.recordSealedCredits(
                utility_addr, -seller_credits
            ))
        else:
            # GRID DISTRIBUTION: public grid rate
            send_admin_tx(web3, contract.functions.recordTrade(
                seller_addr, buyer_addr, t["amount"], t["price"], t["type"]
            ))

    for key, ful in fulfillments.items():
        node_addr = Web3.to_checksum_address(ALL_ACCOUNTS[key]["address"])
        send_admin_tx(web3, contract.functions.recordFulfillment(
            node_addr, ful["percent"], ful["is_producer"]
        ))

    for key, reduced in dr_rewards.items():
        node_addr = Web3.to_checksum_address(ALL_ACCOUNTS[key]["address"])
        send_admin_tx(web3, contract.functions.recordDemandResponse(node_addr, reduced))

    send_admin_tx(web3, contract.functions.settleRound(unserved))

    # Record pricing info
    send_admin_tx(web3, contract.functions.setRoundPricing(round_num, is_peak, grid_rate))

    # IPFS audit trail
    try:
        import pickle, requests as req_lib
        audit = {
            "round": round_num, "utility_supply": utility_supply,
            "grid_rate": grid_rate, "is_peak": is_peak,
            "trades": result_trades, "fulfillments": fulfillments,
            "dr_rewards": dr_rewards, "unserved": unserved,
        }
        files = {'file': ('audit.pkl', pickle.dumps(audit))}
        from config import IPFS_API
        resp = req_lib.post(f"{IPFS_API}/add", files=files)
        if resp.status_code == 200:
            cid = resp.json()['Hash']
            send_admin_tx(web3, contract.functions.setRoundAuditCID(round_num, cid))
    except Exception:
        pass  # IPFS optional

    return True


# Submit bid (called by each participant)

def submit_bid(web3, contract, node_key, address, private_key,
               produced, consumed, ask_price, round_num):
    energy_secret = sec_module.token_hex(16)
    bid_secret    = sec_module.token_hex(16) if ask_price > 0 else ""

    addr = Web3.to_checksum_address(address)

    energy_hash = contract.functions.generateCommitHash(
        produced, consumed, energy_secret).call()
    send_tx(web3, contract.functions.submitCommitment(energy_hash), addr, private_key)

    if ask_price > 0:
        bid_hash = contract.functions.generateBidHash(ask_price, bid_secret).call()
        send_tx(web3, contract.functions.submitBidCommitment(bid_hash), addr, private_key)

    save_bid(round_num, node_key, produced, consumed, ask_price,
             address, energy_secret, bid_secret)

    if "secrets" not in st.session_state:
        st.session_state.secrets = {}
    st.session_state.secrets[round_num] = {
        "energy_secret": energy_secret,
        "bid_secret":    bid_secret,
        "ask_price":     ask_price,
        "produced":      produced,
        "consumed":      consumed,
    }

    # Auto-trigger matching if this was the last submission
    if contract.functions.allCommitted().call():
        rd = contract.functions.getRoundData(round_num).call()
        return process_round(web3, contract, round_num, rd[0])

    return False


# LOGIN PAGE

def show_login():
    st.markdown("## ⚡ GridFlex Chain")
    st.markdown("Decentralized Microgrid Energy Trading")
    st.divider()

    col_form, col_info = st.columns([1, 1])

    with col_form:
        st.markdown("### Login")
        st.caption("Your private key is used only to sign blockchain transactions.")

        selected_name = st.selectbox("Select your node", PARTICIPANT_NAMES)
        private_key   = st.text_input(
            "Private Key", type="password", placeholder="0x...",
            help="Key is verified locally — never transmitted.")

        if st.button("Login", use_container_width=True, type="primary"):
            if not private_key.strip():
                st.error("Please enter your private key.")
                return
            try:
                acct = Account.from_key(private_key.strip())
            except Exception:
                st.error("Invalid private key format.")
                return

            expected = WHITELIST.get(selected_name, "")
            if acct.address.lower() != expected.lower():
                st.error("Private key does not match the selected node. Access denied.")
                return

            node_key = key_for_address(acct.address)
            cfg      = NODE_CONFIG.get(node_key, {})
            st.session_state.update({
                "logged_in":   True,
                "node_name":   selected_name,
                "address":     acct.address,
                "private_key": private_key.strip(),
                "node_key":    node_key,
                "role":        ROLE_NAMES[cfg.get("role", 2)],
                "can_sell":    cfg.get("canSell", False),
                "baseline":    cfg.get("baseline", 0),
                "secrets":     {},
            })
            st.rerun()

    with col_info:
        st.markdown("### Nodes & Roles")
        st.dataframe([
            {"Node": "Utility (Power Grid)", "Role": "UTILITY",    "Priority": "—",       "Notes": "Declares capacity"},
            {"Node": "Home-01",              "Role": "PROSUMER",   "Priority": "Normal",   "Notes": "Solar + DR"},
            {"Node": "Home-02",              "Role": "PROSUMER",   "Priority": "Normal",   "Notes": "Solar + DR"},
            {"Node": "ChemPlant-01",         "Role": "INDUSTRIAL", "Priority": "Normal",   "Notes": "Large consumer"},
            {"Node": "School-01",            "Role": "CRITICAL",   "Priority": "High",     "Notes": "Served 2nd"},
            {"Node": "Clinic-01",            "Role": "CRITICAL",   "Priority": "Highest",  "Notes": "Served 1st"},
        ], use_container_width=True, hide_index=True)

        st.markdown("#### Energy flow")
        st.markdown("""
1. **Utility** starts round, declares available capacity
2. **Each node** submits a sealed cryptographic commitment
3. **Homes with surplus** also seal a feed-in bid price
4. **Auto-match** runs when all 5 nodes have committed
5. **Utility pools** its capacity + purchased feed-in, distributes by priority
6. **Sellers reveal** their bid price to prove auction was fair
        """)


# SIDEBAR

def show_sidebar(contract):
    with st.sidebar:
        st.markdown("### ⚡ GridFlex")
        st.markdown(f'<div class="node-header">{st.session_state.node_name}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="addr-chip">{st.session_state.address}</div>',
                    unsafe_allow_html=True)
        st.markdown("")
        st.caption(f"Role: {st.session_state.role}")

        try:
            info = contract.functions.getNodeInfo(
                Web3.to_checksum_address(st.session_state.address)).call()
            st.metric("Reward Tokens", info[3])
            credits = info[4]
            st.metric("Feed-in Credits", f"+{credits}" if credits >= 0 else str(credits))
        except Exception:
            pass

        st.divider()
        c1, c2 = st.sidebar.columns(2)
        with c1:
            if st.button("Refresh", use_container_width=True):
                st.cache_resource.clear()
                st.rerun()
        with c2:
            if st.button("Logout", use_container_width=True):
                for k in ["logged_in","node_name","address","private_key",
                          "node_key","role","can_sell","baseline","secrets"]:
                    st.session_state.pop(k, None)
                st.rerun()

        st.divider()
        try:
            cr  = contract.functions.currentRound().call()
            blk = get_web3().eth.block_number
            st.caption(f"Round: #{cr}")
            st.caption(f"Block: #{blk}")
            st.caption(f"Node: {NODE_URL}")
        except Exception:
            pass


# COMMITMENT STATUS

def show_commit_status(contract, current_round):
    count = contract.functions.roundCommitCount(current_round).call()
    st.markdown(f"**Submissions: {count} / {COMMITTEE_SIZE}**")
    st.progress(count / COMMITTEE_SIZE if COMMITTEE_SIZE > 0 else 0)

    nc   = contract.functions.nodeCount().call()
    rows = []
    for i in range(nc):
        addr = contract.functions.getNodeAddress(i).call()
        info = contract.functions.getNodeInfo(addr).call()
        if info[1] == 0:   # skip utility
            continue
        done = contract.functions.hasCommitted(current_round, addr).call()
        rows.append({
            "Status":  "Submitted" if done else "Pending",
            "Node":    info[0],
            "Address": f"{addr[:10]}...{addr[-6:]}",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


# RESULTS TABS

def show_results(contract, current_round, user_address, private_key):
    rd = contract.functions.getRoundData(current_round).call()

    # Dynamic pricing info (v3)
    try:
        is_peak   = contract.functions.isPeakRound(current_round).call()
        rate      = contract.functions.roundGridRate(current_round).call()
        audit_cid = contract.functions.roundAuditCID(current_round).call()

        if is_peak:
            st.warning(f"⚠️ Peak pricing active: {rate}c/kWh (demand exceeded available supply)")
        elif rate > 0:
            st.info(f"Normal grid rate: {rate}c/kWh")
    except Exception:
        is_peak, rate, audit_cid = False, 0, ""

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Utility Capacity",   f"{rd[0]} kW")
    c2.metric("Feed-in Purchased",  f"{rd[3]} kW")
    c3.metric("Grid Distributed",   f"{rd[2]} kW")
    c4.metric("Unserved Demand",    f"{rd[5]} kW",
              delta=f"-{rd[5]} kW" if rd[5] > 0 else None,
              delta_color="inverse" if rd[5] > 0 else "off")

    # IPFS audit trail
    if audit_cid:
        st.caption(f"📋 Audit record on IPFS: `{audit_cid}`")

    tab1, tab2, tab3 = st.tabs(["⚡ Fulfillment", "🏆 Feed-in Auction", "🌿 DR Rewards"])

    nc          = contract.functions.nodeCount().call()
    trade_count = contract.functions.getTradeCount().call()

    # ---- TAB 1: FULFILLMENT ----
    with tab1:
        st.markdown("### Grid distribution — who received power and how much")
        st.caption(
            "Clinic (HIGHEST) is served first, School (HIGH) second, others last. "
            "When supply is limited, lower-priority nodes are partially or fully cut. "
            "Percentage shown is the share of each node's total need that was met."
        )

        rows = []
        for i in range(nc):
            addr = contract.functions.getNodeAddress(i).call()
            info = contract.functions.getNodeInfo(addr).call()
            if info[1] == 0:
                continue   # skip utility header
            ful = contract.functions.getFulfillment(current_round, addr).call()
            if not ful[2]:
                continue   # not recorded

            icon = ("🏥" if info[0] == "Clinic-01" else
                    "🏫" if info[0] == "School-01" else
                    "⚡" if ful[1] else "")
            pct  = ful[0]
            rows.append({
                "Priority": PRIO_NAMES[info[2]],
                "":         icon,
                "Node":     info[0],
                "Address":  f"{addr[:10]}...{addr[-6:]}",
                "Status":   "Solar Seller" if ful[1] else "Consumer",
                "% Served": f"{pct}%",
            })

        priority_order = {"HIGHEST": 0, "HIGH": 1, "NORMAL": 2}
        rows.sort(key=lambda r: priority_order.get(r["Priority"], 3))
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Progress bars for consumers
        for r in rows:
            if "Consumer" in r["Status"]:
                pct   = int(r["% Served"].replace("%", ""))
                color = "normal" if pct == 100 else ("off" if pct == 0 else "normal")
                st.progress(pct / 100,
                            text=f"{r['Node'].strip()} — {pct}% of demand met")

        # All trades this round — unified table (grid dist + feed-in)
        st.divider()
        st.markdown("**All trades this round (on-chain):**")
        st.caption(
            "Actual kWh values are hidden. Percentages show each node's share of "
            "total grid distribution or total feed-in. Feed-in bid prices are **sealed** "
            "until the seller voluntarily reveals them."
        )

        # First pass: collect trades and compute totals
        grid_trades  = []  # (seller_name, buyer_name, amount, price, seller_addr)
        feedin_trades = []

        for i in range(trade_count):
            t = contract.functions.getTrade(i).call()
            if t[4] != current_round:
                continue
            si = contract.functions.getNodeInfo(t[0]).call()
            bi = contract.functions.getNodeInfo(t[1]).call()

            if t[5] == 1:
                grid_trades.append((si[0], bi[0], t[2], t[3], t[0]))
            elif t[5] == 2:
                feedin_trades.append((si[0], bi[0], t[2], t[3], t[0]))

        total_grid   = sum(x[2] for x in grid_trades)   if grid_trades   else 1
        total_feedin = sum(x[2] for x in feedin_trades)  if feedin_trades else 1

        # Second pass: build display rows with percentages
        all_trade_rows = []

        for sname, bname, amount, price, seller_addr in feedin_trades:
            pct = round((amount / total_feedin) * 100)
            revealed = contract.functions.hasBidRevealed(current_round, seller_addr).call()
            if revealed:
                bid_price = contract.functions.revealedBidPrice(current_round, seller_addr).call()
                price_str = f"{bid_price}c/kWh"
            else:
                price_str = "🔒 Sealed"
            all_trade_rows.append({
                "Type":             "Home → Utility",
                "From":             sname,
                "To":               bname,
                "Share of Feed-in": f"{pct}%",
                "Price":            price_str,
            })

        for sname, bname, amount, price, seller_addr in grid_trades:
            pct = round((amount / total_grid) * 100)
            all_trade_rows.append({
                "Type":             "Grid → Consumer",
                "From":             sname,
                "To":               bname,
                "Share of Feed-in": f"{pct}%",
                "Price":            f"{price}c/kWh" if price > 0 else "—",
            })

        # Rename column for display
        if all_trade_rows:
            # Use a generic "Share" column name
            for row in all_trade_rows:
                row["Share (%)"] = row.pop("Share of Feed-in")
            st.dataframe(all_trade_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No trades recorded yet.")

    # ---- TAB 2: FEED-IN AUCTION ----
    with tab2:
        st.markdown("### Feed-in auction — homes selling surplus solar to the utility")
        st.caption(
            "Before the round, sellers commit a sealed hash of their ask price. "
            "Utility buys from the cheapest bidder first (reverse auction). "
            "Trade amounts are public but the per-unit bid price is **sealed on-chain** "
            "(stored as 0). After settlement, sellers reveal to prove honesty. "
            "Until revealed, nobody can see what price the utility actually paid."
        )

        # Find feed-in trades
        feedin_sellers = {}   # addr -> {name, amount, price_recorded}
        for i in range(trade_count):
            t = contract.functions.getTrade(i).call()
            if t[4] != current_round or t[5] != 2:
                continue
            si = contract.functions.getNodeInfo(t[0]).call()
            feedin_sellers[t[0]] = {"name": si[0], "amount": t[2]}

        if not feedin_sellers:
            st.info(
                "No feed-in trades this round — either homes had no surplus, "
                "or ask_price was not set."
            )
        else:
            total_fi = sum(info["amount"] for info in feedin_sellers.values()) or 1
            auction_rows = []
            for addr, info in feedin_sellers.items():
                revealed  = contract.functions.hasBidRevealed(current_round, addr).call()
                bid_price = (contract.functions.revealedBidPrice(current_round, addr).call()
                             if revealed else None)
                pct = round((info["amount"] / total_fi) * 100)
                auction_rows.append({
                    "Seller":        info["name"],
                    "Address":       f"{addr[:10]}...{addr[-6:]}",
                    "Share of Feed-in": f"{pct}%",
                    "Bid Price":     f"{bid_price}c/kWh" if revealed else "🔒 Sealed",
                    "Verified":      "✅ Yes" if revealed else "⏳ Pending",
                })
            st.dataframe(auction_rows, use_container_width=True, hide_index=True)

        # Reveal section for the logged-in user
        user_cs       = Web3.to_checksum_address(user_address)
        user_has_bid  = contract.functions.hasBidCommitted(current_round, user_cs).call()
        user_revealed = contract.functions.hasBidRevealed(current_round, user_cs).call()

        if user_has_bid and not user_revealed:
            st.divider()
            st.markdown("#### Reveal Your Feed-in Bid")
            st.info(
                "You submitted a sealed bid price this round. Revealing it proves your ask "
                "price was not changed after other bids were seen. Only your price is "
                "published — your consumption figures stay private."
            )

            secrets_stored = st.session_state.get("secrets", {}).get(current_round, {})

            if secrets_stored.get("bid_secret"):
                st.success(
                    f"Your stored bid: **{secrets_stored['ask_price']}c/kWh** "
                    "(secret in session)"
                )
                if st.button("Reveal My Bid Price", type="primary"):
                    with st.spinner("Verifying on blockchain..."):
                        try:
                            send_tx(
                                get_web3(),
                                get_contract(get_web3()).functions.revealBid(
                                    current_round,
                                    secrets_stored["ask_price"],
                                    secrets_stored["bid_secret"],
                                ),
                                user_cs, private_key,
                            )
                            st.success("Bid price published and verified!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reveal failed: {e}")
            else:
                st.warning("Session secret not available. Enter manually.")
                a_col, s_col = st.columns(2)
                ask_manual    = a_col.number_input("Your ask price (c/kWh)", 1, 30, 6)
                secret_manual = s_col.text_input("Your bid secret")
                if st.button("Submit Manual Reveal"):
                    if not secret_manual:
                        st.error("Secret is required.")
                    else:
                        with st.spinner("Verifying..."):
                            try:
                                send_tx(
                                    get_web3(),
                                    get_contract(get_web3()).functions.revealBid(
                                        current_round, ask_manual, secret_manual
                                    ),
                                    user_cs, private_key,
                                )
                                st.success("Bid revealed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Hash mismatch or invalid secret: {e}")

        elif user_has_bid and user_revealed:
            price = contract.functions.revealedBidPrice(current_round, user_cs).call()
            st.success(f"Your bid of **{price}c/kWh** is verified and publicly recorded.")

    # ---- TAB 3: DR REWARDS ----
    with tab3:
        st.markdown("### Demand Response — who reduced consumption this round")
        st.caption(
            "Home-01 and Home-02 earn **5 tokens per kWh** they consumed less than "
            "their typical baseline (3 kWh). Reducing demand helps the grid during "
            "peak hours and rewards conservation."
        )

        dr_rows = []
        for i in range(nc):
            addr = contract.functions.getNodeAddress(i).call()
            info = contract.functions.getNodeInfo(addr).call()
            red  = contract.functions.demandReductions(current_round, addr).call()
            if red > 0:
                dr_rows.append({
                    "Node":           info[0],
                    "Address":        f"{addr[:10]}...{addr[-6:]}",
                    "Reduced (kWh)":  red,
                    "Tokens Earned":  red * 5,
                })

        if not dr_rows:
            st.info("No demand response events this round.")
        else:
            st.dataframe(dr_rows, use_container_width=True, hide_index=True)

        # All-time leaderboard
        st.divider()
        st.markdown("**All-time DR token leaderboard:**")
        lb = []
        for i in range(nc):
            addr = contract.functions.getNodeAddress(i).call()
            info = contract.functions.getNodeInfo(addr).call()
            if info[3] > 0:
                lb.append({"Node": info[0], "Total Tokens": info[3],
                           "Address": f"{addr[:10]}...{addr[-6:]}"})
        lb.sort(key=lambda x: x["Total Tokens"], reverse=True)
        if lb:
            st.dataframe(lb, use_container_width=True, hide_index=True)
        else:
            st.caption("No tokens earned yet.")


# MAIN APP

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        show_login()
        return

    web3 = get_web3()
    if not web3.is_connected():
        st.error(f"Cannot connect to {NODE_URL}")
        st.stop()

    contract = get_contract(web3)
    if contract is None:
        st.error("Contract not deployed. Run `python deploy_contract.py 8545` first.")
        st.stop()

    user_name    = st.session_state.node_name
    user_address = st.session_state.address
    private_key  = st.session_state.private_key
    node_key     = st.session_state.node_key
    can_sell     = st.session_state.can_sell
    baseline     = st.session_state.baseline
    is_utility   = (st.session_state.role == "UTILITY")

    show_sidebar(contract)

    st.title("⚡ GridFlex Chain")
    st.caption(
        f"**{user_name}** | `{user_address}` | Role: {st.session_state.role}"
    )

    phase, current_round = get_phase(
        contract, Web3.to_checksum_address(user_address))


    # PHASE: IDLE

    if phase == "IDLE":
        st.markdown(
            '<div class="phase-banner phase-idle">Waiting for Utility to start '
            'a new round</div>', unsafe_allow_html=True)

        if is_utility:
            st.markdown("### Start New Round")
            st.info("Declare the utility's available capacity for this hour.")
            cap = st.number_input("Available Capacity (kW)", 1, 200, 30)
            if st.button("Start Round", type="primary", use_container_width=True):
                with st.spinner("Starting on blockchain..."):
                    try:
                        send_admin_tx(web3, contract.functions.startRound(cap))
                        st.success(f"Round started! Utility offering {cap} kW.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("The grid operator will start the round shortly.")


    # PHASE: COMMIT

    elif phase == "COMMIT":
        st.markdown(
            f'<div class="phase-banner phase-commit">Round #{current_round} open '
            f'— submit your sealed bid</div>', unsafe_allow_html=True)

        col_form, col_status = st.columns([1, 1])

        with col_form:
            if is_utility:
                st.info("Round started. Waiting for all participants to submit.")
            else:
                st.markdown("### Submit Your Sealed Bid")
                st.caption(
                    "Your production and consumption figures are **never stored on-chain**. "
                    "A cryptographic hash of your data is committed — nobody can reverse it."
                )

                produced = 0
                if node_key in ["home01", "home02"]:
                    produced = st.number_input(
                        "Solar generation this hour (kW)",
                        0, NODE_CONFIG.get(node_key, {}).get("maxGen", 10), 3,
                        help="How much your panels are producing.")

                consumed = st.number_input(
                    "My energy consumption this hour (kW)",
                    1, 100, baseline or 3,
                    help="Your estimated need this hour.")

                ask_price = 0
                net = produced - consumed

                if can_sell:
                    if net > 0:
                        st.success(
                            f"You have **{net} kW of surplus solar**. "
                            "Submit a feed-in bid to sell it to the utility."
                        )
                        ask_price = st.number_input(
                            "Your ask price (c/kWh)",
                            1, 30, 6,
                            help=(
                                "Sealed bid: utility buys from cheapest bidder first. "
                                "Lower price = more likely to sell. "
                                "You reveal this price after the round to prove honesty."
                            ),
                        )
                        st.info(
                            f"You will offer **{net} kW at {ask_price}c/kWh** to the utility. "
                            "Your consumption ({consumed} kW) stays private."
                        )
                    elif net < 0:
                        st.warning(
                            f"Net: {net} kW — you are consuming more than you produce. "
                            "You will receive power from the grid."
                        )
                    else:
                        st.info("You are exactly self-sufficient this hour (no grid interaction).")

                if st.button("Submit Sealed Bid", type="primary",
                             use_container_width=True):
                    with st.spinner("Hashing and submitting to blockchain..."):
                        try:
                            auto_processed = submit_bid(
                                web3, contract, node_key, user_address,
                                private_key, produced, consumed, ask_price, current_round,
                            )
                            if auto_processed:
                                st.success(
                                    "You were the last participant — "
                                    "matching ran automatically!"
                                )
                            else:
                                st.success(
                                    "Bid sealed and committed to blockchain. "
                                    "Waiting for other participants..."
                                )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Submission failed: {e}")

        with col_status:
            st.markdown("### Submission Progress")
            show_commit_status(contract, current_round)


    # PHASE: WAITING

    elif phase == "WAITING":
        st.markdown(
            f'<div class="phase-banner phase-waiting">Round #{current_round} — '
            f'Your bid is sealed, waiting for other participants...</div>',
            unsafe_allow_html=True)
        st.success("Your bid has been committed to the blockchain.")

        # Show bid secret for the user to save
        secrets_stored = st.session_state.get("secrets", {}).get(current_round, {})
        if secrets_stored.get("bid_secret"):
            st.divider()
            st.warning("Save your bid secret now — you will need it to reveal your bid after settlement.")
            st.code(f"Ask price:  {secrets_stored['ask_price']}c/kWh\nBid secret: {secrets_stored['bid_secret']}", language=None)
            st.caption("Copy the bid secret above and save it. If you refresh the page, the session data will be lost. "
                       "You can also find it later in the round bid file on the admin's machine.")
        elif secrets_stored:
            st.info("You submitted energy data only (no feed-in bid this round).")

        st.markdown("### Submission Progress")
        show_commit_status(contract, current_round)


    # PHASE: READY

    elif phase == "READY":
        st.markdown(
            f'<div class="phase-banner phase-ready">Round #{current_round} — '
            f'All bids received</div>', unsafe_allow_html=True)
        show_commit_status(contract, current_round)

        if is_utility:
            st.divider()
            st.success("All 5 participants have committed. Run the matching to settle this round.")
            rd = contract.functions.getRoundData(current_round).call()
            if st.button("Run Matching and Settle Round",
                         type="primary", use_container_width=True):
                with st.spinner("Running auction and grid distribution..."):
                    if process_round(web3, contract, current_round, rd[0]):
                        st.success("Round settled!")
                        st.rerun()
        else:
            st.info("Waiting for the grid operator to run the matching algorithm...")


    # PHASE: RESULTS

    elif phase == "RESULTS":
        st.markdown(
            f'<div class="phase-banner phase-results">Round #{current_round} '
            f'settled — results on blockchain</div>', unsafe_allow_html=True)

        show_results(contract, current_round, user_address, private_key)

        if is_utility:
            st.divider()
            next_cap = st.number_input(
                "Next round capacity (kW)", 1, 200, 30)
            if st.button(f"Start Round {current_round + 1}",
                         use_container_width=True):
                with st.spinner("Starting next round..."):
                    try:
                        send_admin_tx(web3, contract.functions.startRound(next_cap))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if current_round > 1:
            st.divider()
            with st.expander("View past rounds"):
                sel = st.selectbox(
                    "Round", list(range(1, current_round + 1)),
                    format_func=lambda x: f"Round #{x}",
                )
                show_results(contract, sel, user_address, private_key)


if __name__ == "__main__":
    main()