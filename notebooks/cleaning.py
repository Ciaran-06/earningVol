from earning_vol.clean import load_raw

raw = load_raw("stock-prices")
print(len(raw))                     # 3,563,937
print(raw["ticker"].isna().sum())