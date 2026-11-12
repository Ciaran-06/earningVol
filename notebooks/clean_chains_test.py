from earning_vol.clean import load_raw, clean_chains

raw = load_raw("stock-opts-by-param",tickers=["NVDA"])
df = clean_chains(raw)