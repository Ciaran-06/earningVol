from earning_vol.clean import load_raw, clean_stock_prices, save_clean, clean_calendar, clean_ivx

raw_stock_prices = load_raw("stock-prices")
stock_prices = clean_stock_prices(raw_stock_prices)
save_clean(stock_prices, "stock_prices")

print("===============Stock Prices===============")
print("rows in: ", len(raw_stock_prices))
print("rows out:", len(stock_prices))
print("corporate actions:", stock_prices["corporate_action"].sum())

raw_earning_calendar = load_raw("history-earnings-calendar")
earning_calendar = clean_calendar(raw_earning_calendar)
save_clean(earning_calendar, "earning_calendar")

print("===============Earning Calendar===============")
print("rows in: ", len(raw_earning_calendar))
print("rows out:", len(earning_calendar))
print("Timing codes:", earning_calendar["time_of_day_code"].value_counts())

raw_ivx = load_raw("ivx")
ivx = clean_ivx(raw_ivx)
save_clean(ivx,"ivx")

print("===============IVX Calendar===============")
print("rows in: ", len(raw_ivx))
print("rows out:", len(ivx))
print("Missing Values:", ivx.isna().sum())