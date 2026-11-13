import pandas as pd
import shutil as sh

from earning_vol.config import DERIVED

def load_clean(name, columns=None, tickers=None, start=None, end=None) -> pd.DataFrame:
    path = DERIVED / "clean" / name

    filters = []
    if not path.exists():
        raise ValueError(f"{name} not found on Path: {path}")
    
    if tickers is not None:
        filters.append(("ticker", "in", tickers))
    if start is not None:
        filters.append(("date", ">=", pd.Timestamp(start)))
    if end is not None:
        filters.append(("date", "<=", pd.Timestamp(end)))

    df = pd.read_parquet(path,columns=columns,filters=filters or None)

    if "year" in df.columns:
         df = df.drop(columns=["year"])

    if "ticker" in df.columns:
         df["ticker"] = df["ticker"].astype("str")
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

def save_derived(data,name):
    output_folder = DERIVED / "processed" 

    output_folder.mkdir(parents=True,exist_ok=True)
    data.to_parquet(output_folder/ f"{name}.parquet",index=False)

def load_derived(name, columns=None) -> pd.DataFrame:
    path = DERIVED / "processed" / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{name} not found on Path: {path}")
    df = pd.read_parquet(path,columns=columns)
    return df