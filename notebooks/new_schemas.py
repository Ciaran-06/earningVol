import pandas as pd
from earning_vol.config import DERIVED

summary = pd.read_parquet(DERIVED / "manifest" / "schemas.parquet")
files = pd.read_parquet(DERIVED / "manifest" / "files.parquet")

ds = "stock-opts-by-param"
s = summary[summary["dataset"] == ds]

print("=== 1. files per schema, and the dates they cover ===")
print(s.groupby("schema_id")[["n_files", "first_date", "last_date"]].first().to_string())

print("\n=== 2. columns that differ between schemas ===")
wide = s.pivot(index="column", columns="schema_id", values="type")
print(wide[wide.nunique(axis=1, dropna=False) > 1].to_string())

print("\n=== 3. which tickers have the variant files ===")
v = files[(files["dataset"] == ds) & (files["schema_id"].fillna(0) > 0)]
print(v.groupby("ticker")["trade_date"].agg(["count", "min", "max"]).to_string())