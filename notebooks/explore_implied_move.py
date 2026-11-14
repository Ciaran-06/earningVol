import pandas as pd
from earning_vol.io import load_clean

ENTRY = pd.Timestamp("2023-05-24")      # NVDA reported AMC on the 24th
REACTION = pd.Timestamp("2023-05-25")
ACTUAL_MOVE = 0.244                     # close-to-close, from events.parquet

chain = load_clean("chains", tickers=["NVDA"], start=ENTRY, end=ENTRY)
print("rows on the entry day:", len(chain))
print(chain.columns.tolist())

# ---- 1. Spot: one value from the chain, cross-checked against prices ----
spots = chain["underlying_price"].unique()
print("\nunique underlying_price values:", spots)
spot = float(spots[0])

prices = load_clean("stock_prices", columns=["ticker", "date", "close", "unadjusted_close"],
                    tickers=["NVDA"], start=ENTRY, end=ENTRY)
print(prices.to_string(index=False))
print("unadjusted / adjusted:", round(prices["unadjusted_close"].iloc[0] / prices["close"].iloc[0], 2))

# ---- 2. Expiries on the entry day, and the one we trade ----
expiries = pd.Series(sorted(chain["expiration_date"].unique()))
print(f"\n{len(expiries)} expiries; the first few:", expiries.head(6).dt.date.tolist())
print("strikes per expiry (first few):")
print(chain.groupby("expiration_date")["strike"].nunique().head(6).to_string())

expiry = expiries[expiries >= REACTION].iloc[0]
print("chosen expiry:", expiry.date(), f"({(expiry - ENTRY).days} days after entry)")

# ---- 3. What the quotes look like near the money (before any filtering) ----
leg = chain[chain["expiration_date"] == expiry]
near = leg[(leg["strike"] - spot).abs() / spot < 0.05].sort_values(["strike", "cp"])
print("\nquotes within 5% of spot:")
print(near[["strike", "cp", "bid", "ask", "mid", "preiv"]].to_string(index=False))
print("zero bids near the money:", (near["bid"] <= 0).sum(), "| NaN preiv:", near["preiv"].isna().sum())

# ---- 4. Valid quotes, both legs at the same strike ----
valid = leg[(leg["bid"] > 0) & leg["preiv"].notna()]
print(f"\nrows in chosen expiry: {len(leg)}, with a valid quote: {len(valid)}")

call_strikes = set(valid.loc[valid["cp"] == "C", "strike"])
put_strikes = set(valid.loc[valid["cp"] == "P", "strike"])
both = valid[valid["strike"].isin(call_strikes & put_strikes)]
print("strikes with a valid call AND put:", both["strike"].nunique())

# ---- 5. ATM strike = closest to spot ----
distance = (both["strike"] - spot).abs()
atm_strike = both.loc[distance.idxmin(), "strike"]

# ---- 6. Straddle and implied move ----
legs = both[both["strike"] == atm_strike].set_index("cp")
print("\nthe two legs:")
print(legs[["strike", "expiration_date", "bid", "ask", "mid", "preiv"]].to_string())

call, put = legs.loc["C"], legs.loc["P"]
straddle_bid = call["bid"] + put["bid"]
straddle_mid = call["mid"] + put["mid"]
straddle_ask = call["ask"] + put["ask"]

implied_move = straddle_mid / spot
spread_pct = (straddle_ask - straddle_bid) / straddle_mid

print("\n=============== Summary ===============")
print(f"spot (unadjusted)     : {spot:.2f}")
print(f"expiry                : {expiry.date()}")
print(f"ATM strike            : {atm_strike}")
print(f"straddle bid/mid/ask  : {straddle_bid:.2f} / {straddle_mid:.2f} / {straddle_ask:.2f}")
print(f"bid-ask, % of mid     : {spread_pct:.1%}")
print(f"implied move          : {implied_move:.1%}")
print(f"actual move           : {ACTUAL_MOVE:.1%}")
print(f"realised / implied    : {ACTUAL_MOVE / implied_move:.2f}")