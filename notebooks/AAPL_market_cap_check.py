import pandas as pd
from earning_vol.clean import  load_raw

df = load_raw("history-earnings-calendar")
df = df[df["ticker"] == "AAPL"]
df = df.sort_values(["earning_date"])

print(df[["time_of_day_code","market_cap","earning_date"]].head(12))
print(df[["time_of_day_code","market_cap","earning_date"]].tail(12))