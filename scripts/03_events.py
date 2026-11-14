import pandas as pd

from earning_vol.events import (trading_calendar, add_event_days, add_prices, add_moves,
                                add_hist_move, add_labels, add_straddles)
from earning_vol.clean import available_tickers
from earning_vol.io import load_clean, save_derived
from earning_vol.config import RAW_DATASETS

print("===============Load===============")
prices = load_clean("stock_prices", columns=["ticker", "company", "date", "open", "close", "corporate_action"])
events = load_clean("earning_calendar").drop(columns=["reported_earning"])   # only known after the report
rows_in = len(events)
print("calendar events:", rows_in)

print("===============Event Days===============")
calendar = trading_calendar(prices)
events = add_event_days(events, calendar)
print("events:", len(events))

print("===============Prices and Moves===============")
events = add_prices(events, prices)
events = add_moves(events)
events = add_hist_move(events)
print("events:", len(events))
print("mean r_event:   ", round(events["r_event"].mean(), 5))
print("median abs_move:", round(events["abs_move"].median(), 4))
print("mean gap:       ", round(events["gap"].mean(), 5))

del prices, calendar

print("===============Labels===============")
chain_tickers = available_tickers(RAW_DATASETS["chains"])
events = add_labels(events, chain_tickers)
print("companies with chains:", events.loc[events["has_chains"], "company"].nunique())
print("holdout events:       ", events["is_holdout"].sum())

print("===============Straddles===============")
chains = load_clean("chains", columns=["company", "date", "expiration_date", "strike", "cp",
                                       "bid", "ask", "mid", "preiv", "underlying_price"])
print("chain rows loaded:       ", len(chains))

# keep only rows on an event's entry or reaction day (NVDA alone has 4.26M daily rows)
event_days = pd.concat([
    events[["company", "entry_date"]].rename(columns={"entry_date": "date"}),
    events[["company", "reaction_date"]].rename(columns={"reaction_date": "date"}),
]).drop_duplicates()
chains = chains.merge(event_days, on=["company", "date"], how="inner")
print("chain rows on event days:", len(chains))

events = add_straddles(events, chains)

del chains, event_days

print("===============Save===============")
save_derived(events, "events")
print("rows in: ", rows_in)
print("rows out:", len(events))
print("lost:    ", rows_in - len(events))