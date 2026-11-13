from earning_vol.events import trading_calendar,add_event_days,add_prices,add_moves,add_labels
from earning_vol.clean import available_tickers
from earning_vol.io import load_clean, save_derived

cleaned_prices = load_clean("stock_prices",columns=["ticker","date","company","close","open","corporate_action"])

events = load_clean("earning_calendar")
events = events.drop(columns=["reported_earning"])
pre_proccesing_len = len(events)

calendar = trading_calendar(cleaned_prices)

events = add_event_days(events,calendar)
events = add_prices(events,cleaned_prices)

events = add_moves(events)

print("R_EVENT:           ",events["r_event"].mean())
print("ABS_MOVE:          ",events["abs_move"].median())
print("GAP:               ",events["gap"].mean())

ticker_list = available_tickers("stock-opts-by-param")
events = add_labels(events,ticker_list)
post_proccesing_len = len(events)

print("Lost Event:        ",pre_proccesing_len - post_proccesing_len)
save_derived(events,"events")



