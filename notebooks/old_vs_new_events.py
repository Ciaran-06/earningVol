import pandas as pd

from earning_vol.io import load_derived

new_df = load_derived("events")
old_df = pd.read_parquet(r"D:\DATA\events.parquet")

print("==============Row Count Diff===============")
print("Row Count Old:        ",len(old_df))
print("Row Count New:        ",len(new_df))

print("==============Straddle Status===============")
print("Old Straddle's:       ",old_df["straddle_status"].value_counts())
print("New Straddle's:       ",new_df["straddle_status"].value_counts())

new_df = new_df[new_df["straddle_status"] == "ok"]
old_df = old_df[old_df["straddle_status"] == "ok"]

nvda = new_df[(new_df["company"] == "NVDA") & (new_df["report_date"] == pd.Timestamp("2023-05-24"))]
print("==============Known Info Check===============")
print("Strike:               ", nvda["strike"].iloc[0])
print("Implied Move:         ", nvda["implied_move"].iloc[0])
print("y:                    ", nvda["y"].iloc[0])
print("Days To Expiry:       ", nvda["days_to_expiry"].iloc[0])
print("DTE dtype:            ", new_df["days_to_expiry"].dtype)


new_df = new_df[["company","report_date","strike"]]
old_df = old_df[["company","report_date","strike"]]

df = new_df.merge(old_df, on=["company","report_date"],suffixes=("_new","_old"))
merged_len = len(df)

unchanged = df[df["strike_old"] == df["strike_new"]]

print("==============Mismatched Strike===============")
print("Merged Length:            ",merged_len)
print("Changed Strike's:         ",merged_len - len(unchanged))
print("==============================================")
