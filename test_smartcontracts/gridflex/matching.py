from config import (
    NODE_CONFIG, NORMAL_GRID_RATE, PEAK_GRID_RATE,
    DR_REWARD_RATE, PEAK_THRESHOLD,
)


def detect_peak(utility_supply, total_demand):
    if total_demand == 0:
        return False
    return (utility_supply / total_demand) < PEAK_THRESHOLD


def run_matching(round_data: dict) -> tuple:
    data           = round_data["data"]
    utility_supply = round_data["utility_supply"]

    # Step 1: classify
    feedin_offers  = []
    consumer_needs = {}

    for key, (prod, cons, ask_price) in data.items():
        if key == "utility":
            continue
        surplus = max(0, prod - cons)
        needed  = max(0, cons - prod)
        if surplus > 0 and ask_price > 0:
            feedin_offers.append((ask_price, key, surplus))
        if needed > 0:
            consumer_needs[key] = needed

    # Step 2: detect peak
    total_demand = sum(consumer_needs.values())
    is_peak      = detect_peak(utility_supply, total_demand)
    grid_rate    = PEAK_GRID_RATE if is_peak else NORMAL_GRID_RATE

    # Step 3: gap
    gap = max(0, total_demand - utility_supply)

    # Step 4: competitive feed-in auction
    feedin_offers.sort(key=lambda x: x[0])

    feedin_trades    = []
    total_feedin_kw  = 0
    remaining_gap    = gap
    rejected_sellers = []

    for ask_price, seller_key, surplus in feedin_offers:
        if remaining_gap <= 0:
            rejected_sellers.append((seller_key, "Gap already filled"))
            continue
        if ask_price >= grid_rate:
            rejected_sellers.append((seller_key, f"Ask {ask_price}c >= grid rate {grid_rate}c"))
            continue

        buy_amount = min(surplus, remaining_gap)
        feedin_trades.append({
            "seller": seller_key, "buyer": "utility",
            "amount": buy_amount, "price": ask_price, "type": 2,
        })
        total_feedin_kw += buy_amount
        remaining_gap   -= buy_amount

    # Step 5: pool
    total_pool     = utility_supply + total_feedin_kw
    remaining_pool = total_pool

    # Step 6: distribute by priority
    dist_trades  = []
    fulfillments = {}
    total_served = 0

    buckets = {2: [], 1: [], 0: []}
    for key, need in consumer_needs.items():
        p = NODE_CONFIG.get(key, {}).get("priority", 0)
        buckets[p].append((key, need))

    for p_level in [2, 1, 0]:
        bucket = buckets[p_level]
        if not bucket:
            continue
        total_in_bucket = sum(n for _, n in bucket)

        if remaining_pool >= total_in_bucket:
            for key, need in bucket:
                dist_trades.append({
                    "seller": "utility", "buyer": key,
                    "amount": need, "price": grid_rate, "type": 1,
                })
                remaining_pool -= need
                total_served   += need
                fulfillments[key] = {"percent": 100, "is_producer": False}
        else:
            for key, need in bucket:
                share = int((remaining_pool / total_in_bucket) * need) if total_in_bucket > 0 else 0
                if share > 0:
                    dist_trades.append({
                        "seller": "utility", "buyer": key,
                        "amount": share, "price": grid_rate, "type": 1,
                    })
                    total_served += share
                pct = int((share / need) * 100) if need > 0 else 100
                fulfillments[key] = {"percent": pct, "is_producer": False}
            remaining_pool = 0

    # Sellers who sold
    for t in feedin_trades:
        fulfillments[t["seller"]] = {"percent": 100, "is_producer": True}

    # Rejected sellers
    for seller_key, reason in rejected_sellers:
        if seller_key not in fulfillments:
            fulfillments[seller_key] = {"percent": 0, "is_producer": True}

    # Step 7: DR
    dr_rewards = {}
    for key, (prod, cons, _ask) in data.items():
        if key == "utility":
            continue
        cfg      = NODE_CONFIG.get(key, {})
        baseline = cfg.get("baseline", 0)
        if cfg.get("role") in [1, 3] and baseline > 0 and cons < baseline:
            dr_rewards[key] = baseline - cons

    # Step 8: unserved
    unserved = max(0, total_demand - total_served)

    if rejected_sellers:
        from config import ALL_ACCOUNTS
        print(f"    Rejected sellers:")
        for sk, reason in rejected_sellers:
            print(f"      {ALL_ACCOUNTS[sk]['name']}: {reason}")

    return feedin_trades + dist_trades, fulfillments, dr_rewards, unserved, grid_rate, is_peak
