"""Hand-built tests for pick_straddle: tie rule, closest strike, dead-leg filter.

Run from the repo root:  uv run python notebooks/check_pick_straddle.py
"""
import pandas as pd

from earning_vol.events import pick_straddle

ENTRY = pd.Timestamp("2023-05-24")
REACTION = pd.Timestamp("2023-05-25")
EXPIRY = pd.Timestamp("2023-05-26")


def make_chain(spot: float, put_100_bid: float = 1.0) -> pd.DataFrame:
    """One expiry, strikes 100 and 102, a call and a put at each.

    The 102 rows come FIRST, so the old 'first strike found' rule would pick 102 on a tie.
    """
    rows = [
        # strike, cp, bid,         ask
        (102.0, "C", 1.0,          1.2),
        (102.0, "P", 1.0,          1.2),
        (100.0, "C", 1.0,          1.2),
        (100.0, "P", put_100_bid,  1.2),
    ]
    chain = pd.DataFrame(rows, columns=["strike", "cp", "bid", "ask"])
    chain["mid"] = (chain["bid"] + chain["ask"]) / 2
    chain["preiv"] = 0.5
    chain["underlying_price"] = spot
    chain["expiration_date"] = EXPIRY
    chain["date"] = ENTRY
    return chain


def check(name: str, spot: float, expected_strike: float, **kwargs) -> None:
    result = pick_straddle(make_chain(spot, **kwargs), REACTION)
    got = result["strike"] if isinstance(result, dict) else result
    status = "PASS" if got == expected_strike else "FAIL"
    print(f"{status}  {name}: spot {spot}, expected {expected_strike}, got {got}")


# 1. Tie: spot exactly halfway -> the lower strike must win, even though 102 comes first.
check("tie goes to lower strike", spot=101.0, expected_strike=100.0)

# 2. No tie: the closest strike still wins.
check("closest strike wins", spot=101.4, expected_strike=102.0)

# 3. Dead leg: 100's put has bid 0, so strike 100 is unusable -> 102 even though spot favours 100.
check("dead leg excluded", spot=100.5, expected_strike=102.0, put_100_bid=0.0)