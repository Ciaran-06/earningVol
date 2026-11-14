import pandas as pd

from earning_vol.events import trading_calendar,add_event_days,add_prices,add_moves,add_labels,add_straddles
from earning_vol.clean import available_tickers
from earning_vol.io import load_clean, save_derived
from earning_vol.config import RAW_DATASETS

cleaned_prices = load_clean("stock_prices",columns=["ticker","date","company","close","open","corporate_action"])

events = load_clean("earning_calendar")
events = events.drop(columns=["reported_earning"])
pre_proccesing_len = len(events)

calendar = trading_calendar(cleaned_prices)

events = add_event_days(events,calendar)
events = add_prices(events,cleaned_prices)

del cleaned_prices

events = add_moves(events)

print("R_EVENT:           ",events["r_event"].mean())
print("ABS_MOVE:          ",events["abs_move"].median())
print("GAP:               ",events["gap"].mean())

ticker_list = available_tickers(RAW_DATASETS["chains"])
events = add_labels(events,ticker_list)
post_proccesing_len = len(events)

print("Lost Event:        ",pre_proccesing_len - post_proccesing_len)

chains = load_clean("chains", columns=["company", "date", "expiration_date", "strike", "cp",
                                       "bid", "ask", "mid", "preiv", "underlying_price"])

# keep only chain rows on an event's entry or reaction day (NVDA alone has 4.26M daily rows)
needed = pd.concat([
    events[["company", "entry_date"]].rename(columns={"entry_date": "date"}),
    events[["company", "reaction_date"]].rename(columns={"reaction_date": "date"}),
]).drop_duplicates()
print("chain rows loaded:", len(chains))
chains = chains.merge(needed, on=["company", "date"], how="inner")
print("chain rows on event days:", len(chains))

events = add_straddles(events, chains)
del chains

save_derived(events,"events")


