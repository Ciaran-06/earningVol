from earning_vol.clean import load_raw, clean_stock_prices, save_clean, clean_calendar, clean_ivx, clean_chains
from earning_vol.clean import available_tickers
raw_stock_prices = load_raw("stock-prices")
stock_prices = clean_stock_prices(raw_stock_prices)
save_clean(stock_prices, "stock_prices")

print("===============Stock Prices===============")
print("rows in: ", len(raw_stock_prices))
print("rows out:", len(stock_prices))
print("corporate actions:", stock_prices["corporate_action"].sum())

del raw_stock_prices, stock_prices

raw_earning_calendar = load_raw("history-earnings-calendar")
earning_calendar = clean_calendar(raw_earning_calendar)
save_clean(earning_calendar, "earning_calendar")

print("===============Earning Calendar===============")
print("rows in: ", len(raw_earning_calendar))
print("rows out:", len(earning_calendar))
print("Timing codes:", earning_calendar["time_of_day_code"].value_counts())

del raw_earning_calendar, earning_calendar

raw_ivx = load_raw("ivx")
ivx = clean_ivx(raw_ivx)
save_clean(ivx,"ivx")

print("==================IVX==================")
print("rows in: ", len(raw_ivx))
print("rows out:", len(ivx))
print("Missing Values:", ivx.isna().sum())

del raw_ivx, ivx

rows_in = 0
rows_out = 0

chain_tickers = available_tickers("stock-opts-by-param")
chain_tickers.remove("SPX")
print("Amount of tickers with chains    :",len(chain_tickers))

for ticker in chain_tickers:
    raw_chain = load_raw("stock-opts-by-param",tickers=[ticker])
    rows_in += len(raw_chain)
    chain = clean_chains(raw_chain)
    save_clean(chain,"chains",by_ticker=True)
    rows_out += len(chain)
    print(f"{ticker}: {len(raw_chain)}")
    del chain, raw_chain

print("===============Option Chains===============")
print("rows in: ", rows_in)
print("rows out:", rows_out)