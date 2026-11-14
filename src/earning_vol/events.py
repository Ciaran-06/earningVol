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
    df["abs_move_simple"]= np.abs((df["close_reaction"]/ df["close_entry"]) - 1 )
    return df

def add_labels(events, chain_tickers) -> pd.DataFrame:
    events = events.copy()
    events["has_chains"] = events["company"].isin(chain_tickers)
    events["is_holdout"] = events["report_date"] >= HOLDOUT_START

    return events

def price_exit(exit_day: pd.DataFrame | None, expiry: pd.Timestamp, strike: float) -> dict | str:
    """Prices, on the reaction day, of the same two contracts picked on the entry day.

    No quote filter here: whatever price exists (even a zero bid) is the price you would face.
    Returns a dict, or a short string saying why the exit can't be priced.
    """
    if exit_day is None:
        return "no chain on reaction day"

    legs = exit_day[(exit_day["expiration_date"] == expiry) & (exit_day["strike"] == strike)]
    if set(legs["cp"]) != {"C", "P"}:
        return "no exit quote"

    legs = legs.set_index("cp")
    call, put = legs.loc["C"], legs.loc["P"]
    return {
        "exit_bid": float(call["bid"] + put["bid"]),
        "exit_mid": float(call["mid"] + put["mid"]),
        "exit_ask": float(call["ask"] + put["ask"]),
        "exit_spot": float(exit_day["underlying_price"].iloc[0]),
    }


def add_straddles(events: pd.DataFrame, chains: pd.DataFrame) -> pd.DataFrame:
    """Add the ATM straddle opened at the entry-day close and closed at the reaction-day close.

    Every event of a company that has chains gets a `straddle_status`: "ok", or the reason its
    straddle is missing or incomplete. Events of companies without chains get NaN.
    """
    results = []

    for company, comp_chain in chains.groupby("company", observed=True):
        by_date = {date: day for date, day in comp_chain.groupby("date")}          # {date: that day's chain}
        comp_events = events[events["company"] == company]

        for event in comp_events.itertuples():
            row = {"company": company, "report_date": event.report_date}

            # entry: the straddle on the entry day
            day = by_date.get(event.entry_date)
            if day is None:
                row["straddle_status"] = "no chain on entry day"
                results.append(row)
                continue

            entry = pick_straddle(day, event.reaction_date)
            if isinstance(entry, str):
                row["straddle_status"] = entry
                results.append(row)
                continue
            row.update(entry)

            # exit: the same contracts on the reaction day
            exit_ = price_exit(by_date.get(event.reaction_date), entry["expiry"], entry["strike"])
            if isinstance(exit_, str):
                row["straddle_status"] = exit_          # keep the entry data anyway
            else:
                row.update(exit_)
                row["straddle_status"] = "ok"
            results.append(row)

    out = pd.DataFrame(results)
    print("straddle status:")
    print(out["straddle_status"].value_counts().to_string())

    n_before = len(events)
    events = events.merge(out, on=["company", "report_date"], how="left")
    if len(events) != n_before:
        raise ValueError(f"merge changed the row count: {n_before} -> {len(events)}")
    return events

def pick_straddle(day_chain: pd.DataFrame, reaction_date: pd.Timestamp) -> dict | str:
    """ATM straddle for one event, priced on its entry day.

    Expiry: the earliest one on or after the reaction day (the option must be alive through the move).
    Strike: the one closest to spot among strikes where BOTH the call and the put have a usable
    quote (bid > 0 and preiv present). Ties go to the first strike found.

    Returns a dict of results, or a short string saying why no straddle could be picked.
    """
    # spot: exactly one value per day
    if day_chain["underlying_price"].nunique() != 1:
        return "multiple spots"
    spot = float(day_chain["underlying_price"].iloc[0])

    # expiry: earliest on or after the reaction day
    later = day_chain.loc[day_chain["expiration_date"] >= reaction_date, "expiration_date"]
    if later.empty:
        return "no expiry"
    expiry = later.min()
    chain_exp = day_chain[day_chain["expiration_date"] == expiry]

    # usable quotes, keeping only strikes where both legs are usable
    valid = chain_exp[(chain_exp["bid"] > 0) & chain_exp["preiv"].notna()]
    call_strikes = set(valid.loc[valid["cp"] == "C", "strike"])
    put_strikes = set(valid.loc[valid["cp"] == "P", "strike"])
    valid = valid[valid["strike"].isin(call_strikes & put_strikes)]
    if valid.empty:
        return "no valid strike"

    # ATM strike = closest to spot
    distance = (valid["strike"] - spot).abs()
    atm_strike = valid.loc[distance.idxmin(), "strike"]

    # the two legs (one row each: the contract key guarantees no duplicates)
    legs = valid[valid["strike"] == atm_strike].set_index("cp")
    call, put = legs.loc["C"], legs.loc["P"]

    straddle_bid = call["bid"] + put["bid"]
    straddle_mid = call["mid"] + put["mid"]
    straddle_ask = call["ask"] + put["ask"]

    return {
        "expiry": expiry,
        "strike": float(atm_strike),
        "spot": spot,
        "strike_gap": float((atm_strike - spot) / spot),
        "call_preiv": float(call["preiv"]),
        "put_preiv": float(put["preiv"]),
        "straddle_bid": float(straddle_bid),
        "straddle_mid": float(straddle_mid),
        "straddle_ask": float(straddle_ask),
        "implied_move": float(straddle_mid / spot),
    }

def add_hist_move(events, n=8):
    events = events.sort_values(["company","report_date"])
    events.groupby("company")
    #events.shift(1), (np.rolling(n,min_periods = n)).mean()
    events["hist_move_8"] = events.groupby("company")["abs_move_simple"].transform(lambda s: s.shift(1).rolling(n,min_periods=n).mean())
    missing_value = (events["hist_move_8"].isna()).sum()
    print("Missing Values:      ",missing_value)

    return events

def add_target(events) -> pd.DataFrame:
    df = events.copy()
    df["floored_abs_move_simple"] = np.clip(df["abs_move_simple"],min=0.001)
    print("moves floored at 0.1%:", ((df["straddle_status"] == "ok") & (df["abs_move_simple"] < 0.001)).sum())

    df["move_ratio"] = df["floored_abs_move_simple"].where(df["straddle_status"] == "ok") / df["implied_move"]
    df["y"] = np.log(df["move_ratio"])

    return df