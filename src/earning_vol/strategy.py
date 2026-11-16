import pandas as pd
import numpy as np

def kill_sample(events: pd.DataFrame) -> pd.DataFrame:
    pre_filter_len = len(events)

    events = events[~events["is_holdout"]]
    holdout_len =  len(events)

    events = events[events["straddle_status"] == "ok"]
    straddle_status_len = len(events)

    events = events[events["hist_move_8"].notna()]
    hist_move_len = len(events)

    print("=========Load Kill Sample=========")
    print("Pre-Filter Length:                ", pre_filter_len)
    print("hold-out filter:                  ", holdout_len)
    print("straddle filter:                  ", straddle_status_len)
    print("hist move filter:                 ", hist_move_len)
    print("Earliest Report Date:             ", events["report_date"].min())
    print("Latest Report Date:               ", events["report_date"].max())
    return events

def straddle_pnl(sample: pd.DataFrame, side: str) -> pd.Series:
    if side == "sell":
        sell = sample["straddle_bid"] - np.maximum(sample["exit_ask"],np.abs(sample["exit_spot"] - sample["strike"]))
        sell = sell / sample["straddle_mid"]

        return sell
    elif side == "buy":
        buy = sample["exit_bid"] - sample["straddle_ask"]
        buy = buy / sample["straddle_mid"]

        return buy
    else:
        raise ValueError(f"Must be 'buy' or 'sell' got {side!r}")

def rule_pnl(sample: pd.DataFrame) -> dict:
    buy_side = straddle_pnl(sample,side="buy")
    sell_side = straddle_pnl(sample,side="sell")

    rich = sample["implied_move"] > sample["hist_move_8"]
    cheap = sample["implied_move"] < sample["hist_move_8"]

    return {"always_sell": sell_side, "sell_rich":sell_side[rich], "buy_cheap": buy_side[cheap]}

def summarise(pnl: pd.Series) -> dict:
    if pnl.isna().any():
        raise ValueError(f" {pnl.isna().sum()} NaN Values found in Series") 
    n = pnl.size
    mean = pnl.mean()
    std = pnl.std()
    t = mean / (std / np.sqrt(n))

    return {"n": n, "mean": mean, "std": std, "t": t}

def linear_oos(sample: pd.DataFrame) -> dict:
    x = np.log(sample["hist_move_8"]/ sample["implied_move"])

    y = sample["y"]
    train = (sample["report_date"] < "2019-01-01")
    test = ~train

    b,a = np.polyfit(x[train],y[train],1)
    y_hat = a + b * x[test]
    train_mean = y[train].mean()

    sse_model = ((y[test]- y_hat)**2).sum()
    sse_mean = ((y[test] - train_mean)**2).sum()
    sse_zero = ((y[test] - 0)**2).sum()

    r2_vs_mean = 1 - (sse_model / sse_mean)
    r2_vs_zero = 1- (sse_model / sse_zero)

    n_train = train.sum()
    n_test = test.sum()

    return {
        "n_train": n_train,
        "n_test": n_test,
        "a": a,
        "b": b,
        "r2_vs_mean": r2_vs_mean,
        "r2_vs_zero": r2_vs_zero
    }