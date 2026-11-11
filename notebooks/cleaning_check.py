import pandas as pd
from earning_vol.config import DERIVED
from earning_vol.clean import  load_raw

print(len(pd.read_parquet(DERIVED / "clean" / "stock_prices")))   # should be 3,556,721

raw = load_raw("history-earnings-calendar")
print(raw["time_of_day_code"].count())
print(raw["time_of_day_code"].value_counts())