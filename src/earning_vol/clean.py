import pandas as pd
import pyarrow.parquet as pq
import duckdb as db

from earning_vol.config import DERIVED

def load_raw(dataset) -> pd.DataFrame:
    manifest = pd.read_parquet(DERIVED/"manifest"/"files.parquet")
    rows = manifest[(manifest["dataset"] == dataset) &
                     (manifest["status"] == "parquet") &
                      (~manifest["flag_read_error"]) & 
                      (~manifest["flag_zero_rows"])]
    files = rows["path"].tolist()
    df = db.read_parquet(files,filename=True,union_by_name=True).df()
    df["filename"] = df["filename"].str.replace("\\","/")
    df = df.merge(rows[["path","ticker"]], left_on="filename", right_on="path", how="left")
    df = df.drop(columns=["path"])
    return df
    

