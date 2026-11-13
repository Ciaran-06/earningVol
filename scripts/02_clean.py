from earning_vol.clean import load_raw, clean_stock_prices, clean_calendar, clean_ivx, clean_chains
from earning_vol.io import save_clean
from earning_vol.clean import available_tickers
from earning_vol.config import RAW_DATASETS

print("===============Stock Prices===============")
raw_stock_prices = load_raw(RAW_DATASETS["stock_prices"])
stock_prices = clean_stock_prices(raw_stock_prices)
save_clean(stock_prices, "stock_prices")

print("rows in: ", len(raw_stock_prices))
print("rows out:", len(stock_prices))
print("corporate actions:", stock_prices["corporate_action"].sum())

del raw_stock_prices, stock_prices

print("===============Earning Calendar===============")
raw_earning_calendar = load_raw(RAW_DATASETS["earning_calendar"])
earning_calendar = clean_calendar(raw_earning_calendar)
save_clean(earning_calendar, "earning_calendar")

print("rows in: ", len(raw_earning_calendar))
print("rows out:", len(earning_calendar))
print("Timing codes:", earning_calendar["time_of_day_code"].value_counts())

del raw_earning_calendar, earning_calendar


print("==================IVX==================")
raw_ivx = load_raw(RAW_DATASETS["ivx"])
ivx = clean_ivx(raw_ivx)
save_clean(ivx,"ivx")
print("rows in: ", len(raw_ivx))
print("rows out:", len(ivx))
print("Missing Values:", ivx.isna().sum())

del raw_ivx, ivx

print("===============Option Chains===============")
rows_in = 0
rows_out = 0

chain_tickers = available_tickers(RAW_DATASETS["chains"])
chain_tickers.remove("SPX")
print("Amount of tickers with chains    :",len(chain_tickers))

for ticker in chain_tickers:
    raw_chain = load_raw(RAW_DATASETS["chains"],tickers=[ticker])
    rows_in += len(raw_chain)
    chain = clean_chains(raw_chain)
    save_clean(chain,"chains",by_ticker=True)
    rows_out += len(chain)
    print(f"{ticker}: {len(raw_chain)}")
    del chain, raw_chain

print("rows in: ", rows_in)
print("rows out:", rows_out)