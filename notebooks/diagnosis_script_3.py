import numpy as np
import pandas as pd

from earning_vol.io import load_clean
from earning_vol.events import trading_calendar, add_event_days
from earning_vol.config import START

prices = load_clean("stock_prices", columns=["ticker", "company", "date", "close"])
events = load_clean("earning_calendar").drop(columns=["reported_earning"])

print("calendar first report date:", events["date"].min())
print("prices first date:         ", prices["date"].min())

calendar = trading_calendar(prices)
events = add_event_days(events, calendar)

# ---- entry and reaction prices, WITHOUT dropping anything ----
entry = prices[["company", "date", "close"]].rename(columns={"date": "entry_date", "close": "close_entry"})
reaction = prices[["company", "date", "close"]].rename(columns={"date": "reaction_date", "close": "close_reaction"})
events = events.merge(entry, on=["company", "entry_date"], how="left")
events = events.merge(reaction, on=["company", "reaction_date"], how="left")

# ---- remove bucket 1 (companies with no prices at all) ----
bucket_1 = set(events["company"]) - set(prices["company"])
missing = events[
    (events["close_entry"].isna() | events["close_reaction"].isna())
    & ~events["company"].isin(bucket_1)
].copy()
print("\nmissing events (excluding bucket 1):", len(missing))

# ---- each company's price coverage ----
coverage = prices.groupby("company")["date"].agg(first_price="min", last_price="max").reset_index()
missing = missing.merge(coverage, on="company", how="left")

missing["bucket"] = np.select(
    [missing["entry_date"] < missing["first_price"],
     missing["reaction_date"] > missing["last_price"]],
    ["before_first_price", "after_last_price"],
    default="inside_range",
)
print(missing["bucket"].value_counts())

# ---- detail per bucket ----
cols = ["company", "report_date", "time_of_day_code", "entry_date", "reaction_date",
        "first_price", "last_price", "close_entry", "close_reaction"]

before = missing[missing["bucket"] == "before_first_price"]
print("\n=== before first price ===")
print("of which report_date before START:", (before["report_date"] < START).sum())
print(before["company"].value_counts().head(10))

after = missing[missing["bucket"] == "after_last_price"]
print("\n=== after last price ===")
print(after["company"].value_counts().head(10))

inside = missing[missing["bucket"] == "inside_range"]
print("\n=== inside range (the worrying one) ===")
print(inside["company"].value_counts().head(10))
print(inside[cols].head(20).to_string())