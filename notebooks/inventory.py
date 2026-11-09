import pandas as pd
from earning_vol.manifest import inventory, schemas, contents

df = inventory()
print(df.groupby(["dataset", "status"]).size().unstack(fill_value=0))

files, summary = schemas(df)
print(files.groupby("dataset")["schema_id"].nunique())
print("read errors:", files["error"].notna().sum())
print("total rows:", files["num_rows"].sum())
print(summary[["dataset", "schema_id", "column", "type", "n_files"]].to_string())

cont = contents(df)
print(cont.head())

print("bad dates:", cont["bad_dates"].sum())

chains = df.merge(cont, on="path")
chains = chains[chains["dataset"] == "stock-opts-by-param"]
print("chain date mismatches:", (chains["min_date"] != pd.to_datetime(chains["trade_date"])).sum())