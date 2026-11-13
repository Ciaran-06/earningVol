import pandas as pd
import numpy as np

from earning_vol.clean import available_tickers
from earning_vol.config import HOLDOUT_START

def trading_calendar(prices) -> pd.DatetimeIndex:
    prices = prices[prices["ticker"] == "SPY"]
    dates = prices["date"]
    dates = dates.unique()
    dates = pd.DatetimeIndex(dates)
    dates = dates.sort_values() 

    return dates

def add_event_days(events: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Add entry_date (last close before the news) and reaction_date (first close after it).

    BMO (before market open): the price reacts on the report date itself.
    AMC (after market close): the price reacts on the next trading day.
    """
    events = events.copy().rename(columns={"date": "report_date"})

    # position of the first trading day ON or AFTER / strictly AFTER each report date
    pos_left = calendar.searchsorted(events["report_date"], side="left")
    pos_right = calendar.searchsorted(events["report_date"], side="right")

    reaction_pos = np.where(events["time_of_day_code"] == "BMO", pos_left, pos_right)
    entry_pos = reaction_pos - 1

    beyond_data = reaction_pos >= len(calendar)   # report after the last trading day we have
    no_entry_day = entry_pos < 0                   # report before the first trading day we have
    print("events beyond the data:     ", beyond_data.sum())
    print("events with no entry day:   ", no_entry_day.sum())

    valid = ~beyond_data & ~no_entry_day
    events = events[valid]
    reaction_pos = reaction_pos[valid]
    entry_pos = entry_pos[valid]

    events["entry_date"] = calendar[entry_pos]
    events["reaction_date"] = calendar[reaction_pos]
    return events.reset_index(drop=True)

def add_prices(events,prices):
    events = events.copy()
    pre_merge_len = events.shape[0]
    entry_prices = prices[["company", "date", "close"]].rename(columns={"date": "entry_date", "close": "close_entry"})
    events = events.merge(entry_prices,how="left",on=["company","entry_date"])
    reaction_prices = prices[["company", "date", "open", "close", "corporate_action"]].rename(
    columns={"date": "reaction_date", "open": "open_reaction", "close": "close_reaction"})
    events = events.merge(reaction_prices,how="left",on=["company","reaction_date"])
    post_merge_len = events.shape[0]

    print("Empty Events(close_entry):             ", (events["close_entry"].isna()).sum())
    print("Empty Events(close_reaction):          ", (events["close_reaction"].isna()).sum())
    print("Merge Row Count Diff:                  ", pre_merge_len - post_merge_len)

    events = events[events["close_entry"].notna()]
    events = events[events["close_reaction"].notna()]
    events["corporate_action"] = events["corporate_action"].fillna(False)

    events = events.reset_index(drop=True)

    return events

def add_moves(events) -> pd.DataFrame:
    df = events.copy()
    df["r_event"] = np.log(events["close_reaction"]/ events["close_entry"])
    df["abs_move"] = np.abs(df["r_event"])
    df["gap"] = np.log(events["open_reaction"] / events["close_entry"])
    return df

def add_labels(events, chain_tickers):
    events = events.copy()
    events["has_chains"] = events["company"].isin(chain_tickers)
    events["is_holdout"] = events["report_date"] >= HOLDOUT_START

    return events
