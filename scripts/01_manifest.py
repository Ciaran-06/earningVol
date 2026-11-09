import pandas as pd

from earning_vol.manifest import inventory, schemas, contents
from earning_vol.config import DERIVED

inv = inventory()
files,summary = schemas(inv)
cont = contents(inv)

manifest = (
    inv
    .merge(files[["path", "num_rows", "schema_id", "error"]].rename(columns={"error": "schema_error"}),
           on="path", how="left")
    .merge(cont.rename(columns={"error": "read_error"}), on="path", how="left")
)


for c in ["chunk_start", "chunk_end", "trade_date"]:
    manifest[c] = pd.to_datetime(manifest[c])

m = manifest
m["flag_zero_rows"]      = (m["status"] == "parquet") & (m["num_rows"] == 0)
m["flag_outside_range"]  = (m["min_date"] < m["chunk_start"]) | (m["max_date"] > m["chunk_end"])
m["flag_chain_mismatch"] = m["trade_date"].notna() & ((m["min_date"] != m["trade_date"]) | (m["max_date"] != m["trade_date"]))
m["flag_bad_dates"]      = m["bad_dates"] > 0
m["flag_read_error"]     = m["schema_error"].notna() | m["read_error"].notna()
m["flag_schema_variant"] = m["schema_id"] > 0
m["flag_tmp"]            = m["status"] == "tmp"

flag_cols = [c for c in m.columns if c.startswith("flag_")]
m[flag_cols] = m[flag_cols].fillna(False).astype(bool)   # blanks (e.g. .empty files) -> False
m["any_flag"] = m[flag_cols].any(axis=1)

out = DERIVED / "manifest"
out.mkdir(parents=True, exist_ok=True)
manifest.to_parquet(out / "files.parquet", index=False)
summary.to_parquet(out / "schemas.parquet", index=False)

overview = m.groupby("dataset").agg(
    tickers=("ticker", "nunique"),
    parquet=("status", lambda s: (s == "parquet").sum()),
    empty=("status", lambda s: (s == "empty").sum()),
    rows=("num_rows", "sum"),
    first=("min_date", "min"),
    last=("max_date", "max"),
)
print(overview.to_string())
print(m.groupby("dataset")[flag_cols].sum().to_string())