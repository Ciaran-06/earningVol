import pandas as pd
import numpy as np
import duckdb as db
import shutil as sh

from earning_vol.config import DERIVED

DROP_TICKERS = {"FLT","JEC","PARA"}
REAL_MOVES = {"FMCC", "FNMA","FRCB"}

CONTRACT_KEY = ["company", "date", "expiration_date", "strike", "cp"]


def load_raw(dataset,tickers=None) -> pd.DataFrame:
    manifest = pd.read_parquet(DERIVED/"manifest"/"files.parquet")
    rows = manifest[(manifest["dataset"] == dataset) & 
                     (manifest["status"] == "parquet") &
                      (~manifest["flag_read_error"]) & 
                      (~manifest["flag_zero_rows"])]

    if tickers is not None:
        rows = rows[rows["ticker"].isin(tickers)]

    if rows.empty:
        raise ValueError(f"no files found for tickers={tickers} in dataset {dataset}")

    files = rows["path"].tolist()
    df = db.read_parquet(files,filename=True,union_by_name=True).df()
    df["filename"] = df["filename"].str.replace("\\","/")
    df = df.merge(rows[["path","ticker"]], left_on="filename", right_on="path", how="left")
    df = df.drop(columns=["path"])
    return df

def clean_stock_prices(raw) -> pd.DataFrame:
    df = raw.copy()
    df = df[~df["ticker"].isin(DROP_TICKERS)]
    df["date"] = pd.to_datetime(df["date"])
    df["symbol_at_date"] = df["symbol"] 
    df["company"] = df["ticker"]
    df = df.drop(columns=["record_no","filename","symbol",])
    
    first = ["ticker", "date","company"]
    rest = [c for c in df.columns if c not in first]
    df = df[first + rest]
    df = df.sort_values(["ticker","date"])
    df = df.reset_index(drop=True)
    prev_symbol = df.groupby("ticker")["symbol_at_date"].shift(1)
    jump = np.abs((np.log(df["close"] / df.groupby("ticker")["close"].shift(1))))
    df["corporate_action"] = ((df["symbol_at_date"] != prev_symbol) &
                             (prev_symbol.notna()) &
                             (jump > 0.1) &
                             (~df["ticker"].isin(REAL_MOVES)) & 
                             (~df["symbol_at_date"].str.endswith("Q")))
    
    return df

def save_clean(df, name, by_ticker=False):
    """Save a clean dataset under DERIVED/clean/<name>, split into one folder per year.

    by_ticker=True (for the chains): also split by ticker, and replace only the tickers
    in df, so saving one ticker never deletes the others.
    """
    data = df.copy()
    output_folder = DERIVED / "clean" / name
    data["year"] = data["date"].dt.year

    if by_ticker:
        for t in data["ticker"].unique():
            ticker_folder = output_folder / f"ticker={t}"
            if ticker_folder.exists():
                sh.rmtree(ticker_folder)
        partition_cols = ["ticker", "year"]
    else:
        if output_folder.exists():
            sh.rmtree(output_folder)
        partition_cols = ["year"]

    output_folder.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output_folder, partition_cols=partition_cols, index=False)

def clean_calendar(raw) -> pd.DataFrame:
    # WARNING: reported_earning is the actual EPS released AT the announcement.
    # It is only known after the event, so never use it (or any surprise built from it)
    # as a feature to predict that same event's move. `estimate` is known beforehand and is fine.
    df = raw.copy()
    df = df[~df["ticker"].isin(DROP_TICKERS)]
    df["date"] = pd.to_datetime(df["earning_date"])
    df["time_of_day_code"] = df["time_of_day_code"].str.upper().str.strip()
    df["company"] = df["ticker"]
    df["symbol_at_date"] = df["symbol"]
    df["market_cap"] = df["market_cap"].astype(float)
    df = df.drop(columns=["earning_date","filename","symbol"])
    print("duplicate events:      ", df.duplicated(subset=["company","date"]).sum())
    df = df.drop_duplicates(subset=["company","date"])
    df["time_of_day_code"] = df["time_of_day_code"].where(df["time_of_day_code"].isin(["BMO", "AMC"]), "UNKNOWN")

    first_columns = ["ticker", "company","date"]
    last_columns = [c for c in df.columns if c not in first_columns] 
    df = df[first_columns + last_columns]

    df = df.sort_values(["company","date"])
    df = df.reset_index(drop=True)
    return df

def ivx_rename_helper(name):
    if "IV" in name:
        n = name.lower()
        n = n.split()
        tenor = n[0]
        side  = n[2]
        return "iv_" + tenor + "_" + side
    else:
        return name

def clean_ivx(raw) -> pd.DataFrame:
    df = raw.copy()
    df = df[~df["ticker"].isin(DROP_TICKERS)]
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns=ivx_rename_helper)

    df["symbol_at_date"] = df["symbol"]
    df["company"] = df["ticker"]
    df = df.drop(columns=["symbol","price","record_no","filename"])
    print("duplicate contracts:      ", df.duplicated(subset=["company","date"]).sum())
    df = df.drop_duplicates(subset=["company","date"])
    iv_columns = []
    for c in df.columns:
        if c.startswith("iv_"):
             iv_columns.append(c)
    
    capped_cells = ((df[iv_columns] >= 6).sum()).sum()
    df[iv_columns] = df[iv_columns].where(df[iv_columns] < 6 , np.nan)
    print("iv > 6 contracts:      ", capped_cells)

    first_columns = ["ticker", "company","date"]
    last_columns = [c for c in df.columns if c not in first_columns] 
    df = df[first_columns + last_columns]

    df = df.sort_values(["company","date"])
    df = df.reset_index(drop=True)
    return df

def clean_chains(raw) -> pd.DataFrame:
    df = raw.copy()
    df = df[~df["ticker"].isin(DROP_TICKERS)]

    # renames
    df["date"] = df["c_date"]
    df["cp"] = df["call_put"]
    df["stock_id"] = df["stocks_id"]
    df["strike"] = df["price_strike"]
    df["open_interest"] = df["openinterest"]
    df["otm_pct"] = df["calc_OTM"]
    df["company"] = df["ticker"]
    df["option_id"] = df["option_id"].astype("Int64")
    df["bid"] = df["Bid"]
    df["ask"] = df["Ask"]
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df = df.drop(columns=["c_date", "call_put", "stocks_id", "price_strike", "openinterest",
                          "filename", "calc_OTM", "price", "Bid", "Ask"])

    # real dates before any date comparison
    df["date"] = pd.to_datetime(df["date"])
    df["expiration_date"] = pd.to_datetime(df["expiration_date"])

    # sanity checks: counts only, all should be 0
    print("duplicate contracts:      ", df.duplicated(subset=CONTRACT_KEY).sum())
    print("bid < 0:                  ", (df["bid"] < 0).sum())
    print("ask < bid:                ", (df["ask"] < df["bid"]).sum())
    print("expiration_date < date:   ", (df["expiration_date"] < df["date"]).sum())
    print("cp not C or P:            ", (~df["cp"].isin(["C", "P"])).sum())
    print("strike <= 0:              ", (df["strike"] <= 0).sum())

    df = df.drop_duplicates(subset=CONTRACT_KEY)

    # -1 means "could not be calculated"
    df["preiv"] = df["preiv"].where(df["preiv"] != -1, np.nan)
    df["iv"] = df["iv"].where(df["iv"] != -1, np.nan)

    first_columns = ["ticker", "company", "date", "expiration_date", "strike", "cp"]
    last_columns = [c for c in df.columns if c not in first_columns]
    df = df[first_columns + last_columns]
    df = df.sort_values(first_columns)
    df = df.reset_index(drop=True)
    return df

def available_tickers(dataset) -> list:
    files = pd.read_parquet(DERIVED / "manifest" / "files.parquet")
    files = files[files["dataset"] == dataset]
    files = files[files["status"] == "parquet"]
    files = files["ticker"].unique()

    return sorted(files)