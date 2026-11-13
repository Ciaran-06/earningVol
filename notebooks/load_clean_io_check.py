from earning_vol.io import load_clean

print("stock price dataset:      ",len(load_clean("stock_prices")))
print("NVDA Chains:              ", len(load_clean("chains",tickers=["NVDA"])))
print("Date Column SPY Stock     ", len(load_clean("stock_prices",columns=["date"],tickers=["SPY"])))