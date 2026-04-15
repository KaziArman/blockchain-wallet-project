import streamlit as st
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys, time


# Parse port from command line args (after --) or env var
import os
port = "8545"
for i, arg in enumerate(sys.argv):
    if arg == "--port" and i + 1 < len(sys.argv):
        port = sys.argv[i + 1]

# NODE_URL can be set via environment variable (for Docker)
# Default: localhost for running on host, host.docker.internal for Docker
NODE_URL = os.environ.get("NODE_URL", f"http://localhost:{port}")

# Pre-loaded accounts from genesis (for quick login)
KNOWN_ACCOUNTS = {
    "Jay (Owner)": {
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



@st.cache_resource
def get_web3():
    """Create and cache web3 connection."""
    w3 = Web3(Web3.HTTPProvider(NODE_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


@st.cache_resource
def get_contract(_web3):
    """Load the deployed contract."""
    with open("abi.json", "r") as f:
        abi = json.load(f)
    with open("contract_address.json", "r") as f:
        address = json.load(f)["contract_address"]
    return _web3.eth.contract(
        address=Web3.to_checksum_address(address), abi=abi
    )



def send_transaction(web3, contract_func, sender_address, sender_key, value_wei=0):
    """Build, sign, send a transaction and return receipt."""
    addr = Web3.to_checksum_address(sender_address)
    tx = contract_func.build_transaction({
        "from": addr,
        "nonce": web3.eth.get_transaction_count(addr),
        "gasPrice": "0x0",
        "value": value_wei,
    })
    signed = web3.eth.account.sign_transaction(tx, sender_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt


def to_ether(wei_value):
    """Convert wei to ether as float."""
    return float(Web3.from_wei(wei_value, "ether"))


def shorten(addr):
    """Shorten address for display."""
    return f"{addr[:6]}...{addr[-4:]}"



st.set_page_config(
    page_title="BasicWallet Dashboard",
    page_icon="💰",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .block-container { max-width: 1000px; }

    /* Metric cards — works in both light and dark mode */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 600;
        color: #00d26a;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 16px;
    }

    /* Light mode override */
    @media (prefers-color-scheme: light) {
        div[data-testid="metric-container"] {
            background: #f0f2f6;
            border: 1px solid #e0e2e6;
        }
        div[data-testid="stMetricValue"] {
            color: #0e7a3a;
        }
    }
</style>
""", unsafe_allow_html=True)


# --- Initialize web3 ---
web3 = get_web3()

if not web3.is_connected():
    st.error(f"Cannot connect to blockchain node at {NODE_URL}")
    st.info("Make sure bootnode1 is running and the port is correct.")
    st.stop()

contract = get_contract(web3)
contract_owner = contract.functions.owner().call()


st.sidebar.title("Login")

login_method = st.sidebar.radio(
    "Choose login method:",
    ["Select known account", "Enter manually"],
)

if login_method == "Select known account":
    selected = st.sidebar.selectbox("Account:", list(KNOWN_ACCOUNTS.keys()))
    _address = KNOWN_ACCOUNTS[selected]["address"]
    #_key = KNOWN_ACCOUNTS[selected]["private_key"]
    _key = st.sidebar.text_input("Private key:", type="password", placeholder="0x...")
    _name = selected
else:
    _name = st.sidebar.text_input("Your name:", value="New User")

    # --- Generate New Account Button ---
    if st.sidebar.button("Generate new wallet", use_container_width=True):
        new_acct = web3.eth.account.create()
        st.session_state["generated_address"] = new_acct.address
        st.session_state["generated_key"] = new_acct.key.hex()

        # Auto-fund from Jay (100 ETH)
        jay_addr = Web3.to_checksum_address("0xfe3b557e8fb62b89f4916b721be55ceb828dbd73")
        jay_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
        try:
            tx = {
                "from": jay_addr,
                "to": Web3.to_checksum_address(new_acct.address),
                "value": Web3.to_wei(100, "ether"),
                "nonce": web3.eth.get_transaction_count(jay_addr),
                "gas": 21000,
                "gasPrice": 0,
            }
            signed = web3.eth.account.sign_transaction(tx, jay_key)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            st.session_state["generated_funded"] = True
        except Exception as e:
            st.session_state["generated_funded"] = False
            st.session_state["generated_error"] = str(e)

    # Show generated values or empty fields
    default_addr = st.session_state.get("generated_address", "")
    default_key = st.session_state.get("generated_key", "")

    _address = st.sidebar.text_input("Wallet address:", value=default_addr, placeholder="0x...")
    _key = st.sidebar.text_input("Private key:", value=default_key, type="password", placeholder="0x...")

    if st.session_state.get("generated_funded"):
        st.sidebar.success("New wallet generated and funded with 100 ETH!")
    elif st.session_state.get("generated_error"):
        st.sidebar.error(f"Funding failed: {st.session_state['generated_error']}")
    elif default_addr:
        st.sidebar.info("Wallet generated. Click Login to continue.")

# --- Login Button ---
login_clicked = st.sidebar.button("Login", type="primary", use_container_width=True)

if login_clicked and _address and _key:
    st.session_state["logged_in"] = True
    st.session_state["user_name"] = _name
    st.session_state["user_address"] = _address
    st.session_state["user_key"] = _key

# --- Check if logged in ---
if not st.session_state.get("logged_in", False):
    st.sidebar.divider()
    st.sidebar.subheader("Session Info")
    st.sidebar.info("Please select an account and click Login.")
    st.title("BasicWallet Dashboard")
    st.info("Please login from the sidebar to start using the wallet.")
    st.stop()

# --- User is logged in — load their credentials ---
user_name = st.session_state["user_name"]
user_address = st.session_state["user_address"]
user_key = st.session_state["user_key"]

user_address_cs = Web3.to_checksum_address(user_address)
is_owner = (user_address_cs.lower() == contract_owner.lower())

# --- Sidebar session info ---
st.sidebar.divider()
st.sidebar.subheader("Session Info")
st.sidebar.write(f"**Logged in as:** {user_name}")
st.sidebar.code(user_address_cs, language=None)
if is_owner:
    st.sidebar.success("You are the CONTRACT OWNER")
else:
    st.sidebar.info("You are a regular user")

# Logout button
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

st.sidebar.divider()
st.sidebar.write(f"**Node:** `{NODE_URL}`")
st.sidebar.write(f"**Latest block:** #{web3.eth.block_number}")
st.sidebar.write(f"**Contract:** {shorten(contract.address)}")

# ============================================================
# MAIN PAGE
# ============================================================

st.title("BasicWallet Dashboard")
st.caption(f"Contract: `{contract.address}` | Owner: `{shorten(contract_owner)}`")

# --- Balance Cards ---
col1, col2, col3 = st.columns(3)

wallet_balance = contract.functions.getBalance(user_address_cs).call()
eth_balance = web3.eth.get_balance(user_address_cs)
contract_total = contract.functions.getContractBalance().call()

with col1:
    st.metric("Your wallet balance (in contract)", f"{to_ether(wallet_balance):.4f} ETH")
with col2:
    st.metric("Your ETH balance (on chain)", f"{to_ether(eth_balance):.4f} ETH")
with col3:
    st.metric("Contract total held", f"{to_ether(contract_total):.4f} ETH")

st.divider()

# ============================================================
# TABS
# ============================================================

tab_deposit, tab_withdraw, tab_balances, tab_blocks, tab_history = st.tabs([
    "Deposit", "Withdraw", "All balances", "Block explorer", "Transaction log"
])

# --- DEPOSIT TAB ---
with tab_deposit:
    st.subheader("Deposit ETH into the wallet")
    st.write("Anyone can deposit. The money goes into the smart contract and is tracked under your address.")

    deposit_amount = st.number_input(
        "Amount to deposit (ETH):",
        min_value=0.01,
        max_value=1000.0,
        value=10.0,
        step=1.0,
        key="deposit_amount",
    )

    if st.button("Deposit", type="primary", key="deposit_btn"):
        with st.spinner(f"Depositing {deposit_amount} ETH..."):
            try:
                wei = Web3.to_wei(deposit_amount, "ether")
                tx_hash, receipt = send_transaction(
                    web3, contract.functions.deposit(),
                    user_address, user_key, value_wei=wei
                )
                st.success(f"Deposited {deposit_amount} ETH successfully!")
                st.code(f"Transaction hash: {tx_hash}", language=None)
                st.write(f"Block: #{receipt.blockNumber} | Gas used: {receipt.gasUsed}")

                # Show updated balance
                new_balance = contract.functions.getBalance(user_address_cs).call()
                st.info(f"Your new balance in contract: {to_ether(new_balance):.4f} ETH")
                st.rerun()
            except Exception as e:
                st.error(f"Transaction failed: {str(e)}")


# --- WITHDRAW TAB ---
with tab_withdraw:
    st.subheader("Withdraw from depositors")

    if not is_owner:
        st.warning("Only the contract owner (Jay) can withdraw. You are logged in as a regular user.")
        st.write("If you try to withdraw, the smart contract will reject your transaction.")

        if st.button("Try to withdraw anyway (will fail)", key="fail_withdraw"):
            with st.spinner("Sending transaction..."):
                try:
                    send_transaction(
                        web3, contract.functions.withdrawFromAll(10),
                        user_address, user_key
                    )
                    st.error("This should not have succeeded!")
                except Exception as e:
                    st.error(f"Transaction reverted (as expected): Only owner can withdraw")
                    st.info("The contract's `onlyOwner` modifier blocked this transaction. "
                            "Your identity (address) did not match the owner's address.")
    else:
        st.success("You are the owner. You can withdraw a percentage from depositors.")

        withdraw_mode = st.radio(
            "Withdrawal mode:",
            ["Withdraw from ALL depositors", "Withdraw from ONE depositor"],
        )

        if withdraw_mode == "Withdraw from ALL depositors":
            pct = st.slider("Percentage to withdraw:", 1, 100, 20, key="withdraw_all_pct")

            # Preview
            st.write("**Preview:**")
            depositor_count = contract.functions.getDepositorCount().call()
            preview_total = 0
            preview_data = []
            for i in range(depositor_count):
                dep_addr = contract.functions.getDepositor(i).call()
                dep_bal = contract.functions.getBalance(dep_addr).call()
                take = (dep_bal * pct) // 100
                remaining = dep_bal - take
                preview_data.append({
                    "Address": shorten(dep_addr),
                    "Current": f"{to_ether(dep_bal):.4f} ETH",
                    f"Take ({pct}%)": f"{to_ether(take):.4f} ETH",
                    "Remaining": f"{to_ether(remaining):.4f} ETH",
                })
                preview_total += take

            if preview_data:
                st.table(preview_data)
                st.write(f"**Total you will receive: {to_ether(preview_total):.4f} ETH**")

            if st.button(f"Withdraw {pct}% from all", type="primary", key="do_withdraw_all"):
                with st.spinner("Processing withdrawal..."):
                    try:
                        tx_hash, receipt = send_transaction(
                            web3, contract.functions.withdrawFromAll(pct),
                            user_address, user_key
                        )
                        st.success(f"Withdrawn {pct}% from all depositors!")
                        st.code(f"Transaction hash: {tx_hash}", language=None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")

        else:  # Withdraw from ONE
            depositor_count = contract.functions.getDepositorCount().call()
            if depositor_count == 0:
                st.info("No depositors yet.")
            else:
                depositor_addrs = []
                for i in range(depositor_count):
                    addr = contract.functions.getDepositor(i).call()
                    bal = contract.functions.getBalance(addr).call()
                    depositor_addrs.append(f"{shorten(addr)} — {to_ether(bal):.4f} ETH")

                selected_idx = st.selectbox("Select depositor:", range(len(depositor_addrs)),
                                            format_func=lambda i: depositor_addrs[i],
                                            key="select_depositor")
                target_addr = contract.functions.getDepositor(selected_idx).call()

                pct_one = st.slider("Percentage:", 1, 100, 50, key="withdraw_one_pct")

                if st.button(f"Withdraw {pct_one}% from {shorten(target_addr)}", type="primary",
                             key="do_withdraw_one"):
                    with st.spinner("Processing..."):
                        try:
                            tx_hash, receipt = send_transaction(
                                web3,
                                contract.functions.withdrawFromDepositor(target_addr, pct_one),
                                user_address, user_key
                            )
                            st.success(f"Withdrawn {pct_one}% from {shorten(target_addr)}!")
                            st.code(f"Transaction hash: {tx_hash}", language=None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {str(e)}")


# --- ALL BALANCES TAB ---
with tab_balances:
    st.subheader("All depositor balances")

    depositor_count = contract.functions.getDepositorCount().call()

    if depositor_count == 0:
        st.info("No deposits yet. Be the first to deposit!")
    else:
        balances_data = []
        for i in range(depositor_count):
            dep_addr = contract.functions.getDepositor(i).call()
            dep_bal = contract.functions.getBalance(dep_addr).call()

            # Find name if known
            name = "Unknown"
            for n, acct in KNOWN_ACCOUNTS.items():
                if Web3.to_checksum_address(acct["address"]).lower() == dep_addr.lower():
                    name = n
                    break

            is_you = "(you)" if dep_addr.lower() == user_address_cs.lower() else ""

            balances_data.append({
                "Name": f"{name} {is_you}",
                "Address": shorten(dep_addr),
                "Balance": f"{to_ether(dep_bal):.4f} ETH",
            })

        st.table(balances_data)
        st.metric("Contract total", f"{to_ether(contract_total):.4f} ETH")

    if st.button("Refresh", key="refresh_balances"):
        st.rerun()


# --- BLOCK EXPLORER TAB ---
with tab_blocks:
    st.subheader("Recent blocks")

    latest_block = web3.eth.block_number
    num_blocks = st.slider("How many recent blocks to show:", 5, 50, 10, key="num_blocks")

    start_block = max(0, latest_block - num_blocks + 1)

    blocks_data = []
    for bn in range(latest_block, start_block - 1, -1):
        block = web3.eth.get_block(bn)
        blocks_data.append({
            "Block #": bn,
            "Transactions": len(block.transactions),
            "Gas used": block.gasUsed,
            "Timestamp": time.strftime("%H:%M:%S", time.gmtime(block.timestamp)),
            "Hash": shorten(block.hash.hex()),
        })

    st.dataframe(blocks_data, use_container_width=True, hide_index=True)

    # Block detail
    block_num = st.number_input("Inspect block #:", min_value=0, max_value=latest_block,
                                value=latest_block, key="inspect_block")
    block_detail = web3.eth.get_block(block_num, full_transactions=True)

    st.write(f"**Block #{block_num}**")
    st.write(f"- Hash: `{block_detail.hash.hex()}`")
    st.write(f"- Parent: `{shorten(block_detail.parentHash.hex())}`")
    st.write(f"- Transactions: {len(block_detail.transactions)}")
    st.write(f"- Gas used: {block_detail.gasUsed}")
    st.write(f"- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(block_detail.timestamp))}")

    if block_detail.transactions:
        st.write("**Transactions in this block:**")
        for tx in block_detail.transactions:
            with st.expander(f"Tx: {shorten(tx.hash.hex())}"):
                st.write(f"- From: `{tx['from']}`")
                st.write(f"- To: `{tx['to'] if tx['to'] else 'Contract creation'}`")
                st.write(f"- Value: {to_ether(tx['value']):.4f} ETH")
                st.write(f"- Gas: {tx['gas']}")


# --- TRANSACTION LOG TAB ---
with tab_history:
    st.subheader("Your transaction history")
    st.write(f"Scanning recent blocks for transactions from `{shorten(user_address_cs)}`...")

    scan_range = st.slider("Scan last N blocks:", 10, 200, 50, key="scan_range")
    latest = web3.eth.block_number
    start = max(0, latest - scan_range)

    my_txs = []
    with st.spinner(f"Scanning blocks {start} to {latest}..."):
        for bn in range(latest, start - 1, -1):
            block = web3.eth.get_block(bn, full_transactions=True)
            for tx in block.transactions:
                if tx["from"].lower() == user_address_cs.lower():
                    receipt = web3.eth.get_transaction_receipt(tx.hash)
                    my_txs.append({
                        "Block": bn,
                        "Tx hash": shorten(tx.hash.hex()),
                        "To": shorten(tx["to"]) if tx["to"] else "Deploy",
                        "Value": f"{to_ether(tx['value']):.4f} ETH",
                        "Status": "Success" if receipt.status == 1 else "Failed",
                        "Gas used": receipt.gasUsed,
                    })

    if my_txs:
        st.dataframe(my_txs, use_container_width=True, hide_index=True)
        st.write(f"Found {len(my_txs)} transactions in last {scan_range} blocks.")
    else:
        st.info(f"No transactions found in the last {scan_range} blocks.")