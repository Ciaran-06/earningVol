import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import duckdb as db
import shutil as sh

from earning_vol.config import DERIVED

DROP_TICKERS = {"FLT","JEC","PARA"}
REAL_MOVES = {"FMCC", "FNMA"}

def load_raw(dataset,tickers=None) -> pd.DataFrame:
    manifest = pd.read_parquet(DERIVED/"manifest"/"files.parquet")
    rows = manifest[(manifest["dataset"] == dataset) & 
                     (manifest["status"] == "parquet") &
                      (~manifest["flag_read_error"]) & 
                      (~manifest["flag_zero_rows"])]

    if tickers is not None:
        rows = rows[rows["ticker"].isin(tickers)]

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

def save_clean(df,name):
    data = df.copy()
    output_folder = DERIVED / "clean" / name
    if output_folder.exists():
        sh.rmtree(output_folder)

    data["year"] = data["date"].dt.year
    output_folder.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output_folder,partition_cols=["year"], index=False)