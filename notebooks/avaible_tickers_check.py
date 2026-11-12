from earning_vol.clean import available_tickers

print(available_tickers("stock-opts-by-param"))
print(f"Ticker List Size {len(available_tickers("stock-opts-by-param"))}")