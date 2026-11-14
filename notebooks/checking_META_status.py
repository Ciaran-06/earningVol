from earning_vol.io import load_clean
from earning_vol.config import RAW_DATASETS

df = load_clean("earning_calendar",tickers=["META"])
unique_years = df["date"].dt.year.value_counts()
unique_years = unique_years.sort_index()
print(unique_years)
