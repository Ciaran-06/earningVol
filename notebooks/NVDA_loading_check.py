import pandas as pd

from earning_vol.clean import load_raw, clean_chains, save_clean
from earning_vol.config import DERIVED

CHAINS = DERIVED / "clean" / "chains"
NVDA = [("ticker", "=", "NVDA")]

raw = load_raw("stock-opts-by-param", tickers=["NVDA"])
print(f"raw rows:          {len(raw)}")
df = clean_chains(raw)
print(f"cleaned rows:      {len(df)}")

# save 1
save_clean(df, "chains", by_ticker=True)
back = pd.read_parquet(CHAINS, filters=NVDA)
print(f"after 1st save:    {len(back)}")

# save 2: must not double anything
save_clean(df, "chains", by_ticker=True)
back = pd.read_parquet(CHAINS, filters=NVDA)
print(f"after 2nd save:    {len(back)}")
