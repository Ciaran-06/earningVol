from earning_vol.clean import load_raw, clean_stock_prices

raw = load_raw("stock-prices")
print("raw rows:", len(raw), "| missing tickers:", raw["ticker"].isna().sum())

prices = clean_stock_prices(raw)
print("clean rows:", len(prices))

checks = {
    "close <= 0":          (prices["close"] <= 0).sum(),
    "close missing":       prices["close"].isna().sum(),
    "high < low":          (prices["high"] < prices["low"]).sum(),
    "close outside range": ((prices["close"] < prices["low"]) | (prices["close"] > prices["high"])).sum(),
    "duplicate rows":      prices.duplicated(subset=["company", "date"]).sum(),
}
for name, n in checks.items():
    print(f"{name:22s} {n}")

print("corporate actions:", prices["corporate_action"].sum())
print(prices.loc[prices["corporate_action"], ["ticker", "date", "symbol_at_date", "close"]].to_string())