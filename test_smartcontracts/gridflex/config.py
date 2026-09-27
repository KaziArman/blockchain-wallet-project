# PRICING (credits per kWh)
NORMAL_GRID_RATE  = 12   # c/kWh — buying from utility in normal conditions
PEAK_GRID_RATE    = 14   # c/kWh — buying from utility when demand > supply
DR_REWARD_RATE    = 5    # tokens per kWh reduced below baseline
PEAK_THRESHOLD    = 0.8  # if utility_supply covers < 80% of demand → peak mode

# IPFS endpoint (from inside test-smartcontracts container)
IPFS_API = "http://host.docker.internal:5001/api/v0"

# ACCOUNTS

GRID_ADMIN = {
    "name":        "Grid Admin",
    "address":     "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
    "private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63",
}

UTILITY = {
    "name":        "Utility (Power Grid)",
    "address":     "0x4c7C6e60b4e0EA45DC33C1fc7D28497A29F36F7d",
    "private_key": "0xa0a7d0feb4a1110a2d25572b4f5c38a5a93844df1a74be92b4d3c7ed1004aab3",
}

HOME_01 = {
    "name":        "Home-01",
    "address":     "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
    "private_key": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3",
}

HOME_02 = {
    "name":        "Home-02",
    "address":     "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
    "private_key": "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f",
}

CHEMPLANT = {
    "name":        "ChemPlant-01",
    "address":     "0xc610E5F797b1Aef603b4319A0024691Bb42Bd999",
    "private_key": "0x4ae649a1f892f210c57048ad27bafc593a9f3280556d3aaf31db427c009e585a",
}

SCHOOL = {
    "name":        "School-01",
    "address":     "0x8099948Ea5F0712823D1ba84e542AF5d5118e3FC",
    "private_key": "0x7b3f4654c0861f1fe3c56a10c6809f8db5166f49c802553ae4ac9172dbc8a84d",
}

CLINIC = {
    "name":        "Clinic-01",
    "address":     "0x3aE689841E16684cE3Ac9b61587E2599912905F2",
    "private_key": "0xc8dcd1de0c98961a89f074ce023eb6341f6c8c038371404d7f5764d336c807cc",
}

ALL_ACCOUNTS = {
    "admin":     GRID_ADMIN,
    "utility":   UTILITY,
    "home01":    HOME_01,
    "home02":    HOME_02,
    "chemplant": CHEMPLANT,
    "school":    SCHOOL,
    "clinic":    CLINIC,
}

# NODE CONFIG — OFF-CHAIN private data (never stored on-chain)
NODE_CONFIG = {
    "utility":   {"role": 0, "priority": 0, "maxGen": 60, "baseline": 0,  "canSell": False},
    "home01":    {"role": 1, "priority": 0, "maxGen": 10, "baseline": 3,  "canSell": True},
    "home02":    {"role": 1, "priority": 0, "maxGen": 8,  "baseline": 3,  "canSell": True},
    "chemplant": {"role": 4, "priority": 0, "maxGen": 0,  "baseline": 30, "canSell": False},
    "school":    {"role": 5, "priority": 1, "maxGen": 0,  "baseline": 8,  "canSell": False},
    "clinic":    {"role": 5, "priority": 2, "maxGen": 0,  "baseline": 6,  "canSell": False},
}

COMMITTEE_MEMBERS = ["home01", "home02", "chemplant", "school", "clinic"]
COMMITTEE_SIZE    = len(COMMITTEE_MEMBERS)

WHITELIST = {
    "Utility (Power Grid)": "0x4c7C6e60b4e0EA45DC33C1fc7D28497A29F36F7d",
    "Home-01":              "0x627306090abaB3A6e1400e9345bC60c78a8BEf57",
    "Home-02":              "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
    "ChemPlant-01":         "0xc610E5F797b1Aef603b4319A0024691Bb42Bd999",
    "School-01":            "0x8099948Ea5F0712823D1ba84e542AF5d5118e3FC",
    "Clinic-01":            "0x3aE689841E16684cE3Ac9b61587E2599912905F2",
}

PARTICIPANT_NAMES = list(WHITELIST.keys())

ADDRESS_TO_KEY = {
    v["address"].lower(): k
    for k, v in ALL_ACCOUNTS.items()
    if k != "admin"
}

def get_account_by_name(display_name: str) -> dict:
    for acct in ALL_ACCOUNTS.values():
        if acct["name"] == display_name:
            return acct
    return {}

def get_config_by_key(key: str) -> dict:
    return NODE_CONFIG.get(key, {})

def key_for_address(address: str) -> str:
    for k, v in ALL_ACCOUNTS.items():
        if v["address"].lower() == address.lower():
            return k
    return ""
