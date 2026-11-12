import pandas as pd

from earning_vol.config import RAW
from earning_vol.clean import load_raw

df = load_raw("stock-opts-by-param",tickers=["NVDA"])
df = df[df["ticker"] == "NVDA"]
print(df.shape[0])
print(df.columns)
print(df["call_put"].describe)
print("==========invalid iv===============")
print(df[df["iv"] == -1])
print("==========invalid preiv===============")
print(df[df["preiv"] == -1])

print("==========no bid===============")
print(df[df["Bid"] == 0])
print("==========ask < bid ===============")
print(df[df["Ask"] < df["Bid"]])
print("============descritpion ==============")
print(df[["price","calc_OTM","is_settlement"]].head(10))\

print("=============================Mid Check====================")
calc_mid = (df["Bid"] + df["Ask"]) / 2
diff = (df["price"] - calc_mid).abs()

print("rows where price == mid (within 1 cent):", (diff <= 0.01).mean())
print(df.loc[diff > 0.01, ["c_date", "price_strike", "call_put", "Bid", "Ask", "price"]].head(10))