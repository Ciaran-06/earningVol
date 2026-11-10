from earning_vol.clean import load_raw, clean_stock_prices, save_clean

raw = load_raw("stock-prices")
prices = clean_stock_prices(raw)
save_clean(prices, "stock_prices")

print("rows in: ", len(raw))
print("rows out:", len(prices))
print("corporate actions:", prices["corporate_action"].sum())
