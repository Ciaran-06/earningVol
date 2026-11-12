import pandas as pd

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
