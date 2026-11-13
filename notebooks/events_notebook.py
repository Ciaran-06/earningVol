import pandas as pd

from earning_vol.events import trading_calendar,add_event_days,add_prices,add_moves,add_labels
from earning_vol.clean import available_tickers
from earning_vol.io import load_clean
from earning_vol.config import DERIVED

prices = load_clean("stock_prices")

events = load_clean("earning_calendar")
events = events.drop(columns=["reported_earning"])

calendar = trading_calendar(prices)
events = add_event_days(events,calendar)
events = add_prices(events,prices)

moves = add_moves(events)
print("R_EVENT:           ",moves["r_event"].iloc[0])
print("ABS_MOVE:          ",moves["abs_move"].iloc[0])
print("GAP:               ",moves["gap"].iloc[0])

ticker_list = available_tickers("stock-opts-by-param")
lables = add_labels(events,ticker_list)
print("==============Labeld Data===============")
print(lables)