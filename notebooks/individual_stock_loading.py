from earning_vol.clean import load_raw, clean_stock_prices

df1 = load_raw("stock-prices")                          # everything, as before
df2 = load_raw("stock-opts-by-param", tickers=["NVDA"]) # just NVDA

print(df1.head(5))
print(df2.head(5))