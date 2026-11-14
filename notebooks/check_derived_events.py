import numpy as np
import pandas as pd

from earning_vol.io import load_clean, load_derived
from earning_vol.events import trading_calendar

events = load_derived("events")
print("events:", len(events))

# ---- 1. Famous events ----
print("\n=== 1. Famous events ===")
famous = [("NVDA", "2023-05-24"), ("META", "2022-02-02"), ("NFLX", "2022-04-19")]
cols = ["company", "report_date", "time_of_day_code", "entry_date", "reaction_date",
        "close_entry", "close_reaction", "r_event"]
for company, date in famous:
    d = pd.Timestamp(date)
    near = events[(events["company"] == company) & ((events["report_date"] - d).abs() <= pd.Timedelta(days=3))]
    if near.empty:
        print(f"{company} {date}: NOT FOUND")
    else:
        out = near[cols].copy()
        out["pct_move"] = np.expm1(out["r_event"]).round(3)   # log return -> % move
        print(out.to_string(index=False))

# ---- 2. Chains ----
print("\n=== 2. Chains ===")
chain_col = "has_chains" if "has_chains" in events.columns else "has_chain"
print("companies with chains:", events.loc[events[chain_col], "company"].nunique(), "(expect 49)")
print("events with chains:   ", events[chain_col].sum())

# ---- 3. Holdout ----
print("\n=== 3. Holdout ===")
print(events["is_holdout"].value_counts())
print(events["is_holdout"].value_counts(normalize=True).round(3))

# ---- 4. Corporate actions ----
print("\n=== 4. Corporate actions ===")
print("events on a corporate-action day:", events["corporate_action"].sum())
print(events.loc[events["corporate_action"], ["company", "report_date", "reaction_date", "r_event"]].to_string(index=False))

# ---- 5. Timing test ----
print("\n=== 5. Timing test ===")
prices = load_clean("stock_prices", columns=["ticker", "company", "date", "close"])
calendar = trading_calendar(prices)

prices = prices.sort_values(["company", "date"])
prices["ret"] = np.log(prices["close"]).groupby(prices["company"]).diff()   # daily log return
rets = prices[["company", "date", "ret"]]

reaction_pos = calendar.searchsorted(events["reaction_date"])
medians = {}
for k in range(-3, 4):                                  # trading days relative to the reaction day
    p = reaction_pos + k
    ok = (p >= 0) & (p < len(calendar))
    tmp = events.loc[ok, ["company"]].reset_index(drop=True)
    tmp["date"] = calendar[p[ok]]
    tmp = tmp.merge(rets, on=["company", "date"], how="left")
    medians[k] = tmp["ret"].abs().median()

print("median |daily return| around the reaction day:")
for k, v in medians.items():
    print(f"  day {k:+d}: {v:.4f}" + ("   <- reaction day" if k == 0 else ""))
print("reaction / average of days -1 and +1:", round(medians[0] / np.mean([medians[-1], medians[1]]), 2), "(expect ~3)")