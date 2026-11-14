import pandas as pd

from earning_vol.clean import load_raw
from earning_vol.config import RAW_DATASETS

df = load_raw(RAW_DATASETS["ivs"])

print(df.columns)
print(df["symbol"].unique())