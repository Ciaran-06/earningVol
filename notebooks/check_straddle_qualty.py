"""Straddle quality checks for METHODS §4.

1. Is either known crossed quote (ask < bid) a leg of an `ok` straddle, at entry or exit?
2. How far past the reaction day do the chosen expiries run, by year?

Run from the repo root:  uv run python notebooks/check_straddle_quality.py
"""
import numpy as np
from earning_vol.io import load_clean, load_derived

events = load_derived("events")
ok = events[events["straddle_status"] == "ok"]

intrensic = ok[ok["exit_ask"] < np.abs(ok["exit_spot"] - ok["strike"])]
print(intrensic[["company","report_date","strike","exit_spot","exit_bid","exit_ask"]])

print("exit ask <= exit_bid:    ", len(ok[ok["exit_ask"] <= ok["exit_bid"]]))
print("exit_ask < |exit_spot - strike|: ", len(intrensic))

# ---------------------------------------------------------------- 1. crossed quotes
chains = load_clean("chains", tickers=["TSLA", "JPM"])
crossed = chains[chains["ask"] < chains["bid"]]

print(chains["company"].value_counts())
print("============== Crossed Quotes ==============")
print("crossed rows (ask < bid):", len(crossed))
print(crossed[["company", "date", "expiration_date", "strike", "cp", "bid", "ask"]].to_string(index=False))

matches = 0
for row in crossed.itertuples():
    hit = ok[
        (ok["company"] == row.company)
        & (ok["expiry"] == row.expiration_date)
        & (ok["strike"] == row.strike)
        & ((ok["entry_date"] == row.date) | (ok["reaction_date"] == row.date))
    ]
    if not hit.empty:
        print(f"\nUSED: {row.company} {row.date.date()} {row.cp} {row.strike}")
        print(hit[["company", "report_date", "entry_date", "reaction_date", "expiry", "strike"]].to_string(index=False))
    matches += len(hit)

print("\nok straddles using a crossed quote:", matches)

# ---------------------------------------------------------------- 2. days to expiry by year
year = ok["report_date"].dt.year
dte_by_year = ok.groupby(year).agg(
    events=("days_to_expiry", "size"),
    median_dte=("days_to_expiry", "median"),
    share_le_7=("days_to_expiry", lambda s: (s <= 7).mean()),
)

print("\n============== Days To Expiry by Year (ok events) ==============")
print(dte_by_year.round(2).to_string())