import pandas as pd
from earning_vol.config import DERIVED

CLEAN = DERIVED / "clean"

# 1. Which days are flagged as corporate actions? (expect 11)
prices = pd.read_parquet(CLEAN / "stock_prices")
flagged = prices.loc[prices["corporate_action"], ["ticker", "date", "symbol_at_date", "close"]]
print(flagged.sort_values(["ticker", "date"]).to_string())


# 2. Is any company stored under two folders? (same symbol on the same date in two tickers)
def cross_folder_dups(df, name):
    d = df[df.duplicated(subset=["symbol_at_date", "date"], keep=False)]
    print(f"\n{name}: {d['symbol_at_date'].nunique()} symbol(s) appear under more than one folder")
    if len(d):
        print(d.groupby(["symbol_at_date", "ticker"], observed=True)["date"]
                .agg(["count", "min", "max"]).to_string())


cross_folder_dups(prices, "stock_prices")
cross_folder_dups(pd.read_parquet(CLEAN / "ivx", columns=["ticker", "date", "symbol_at_date"]), "ivx")
cross_folder_dups(pd.read_parquet(CLEAN / "earning_calendar", columns=["ticker", "date", "symbol_at_date"]),
                  "earning_calendar")


# 3. Did every dataset save exactly what 02_clean produced?
expected = {"stock_prices": 3_639_381, "earning_calendar": 48_035, "ivx": 3_549_501, "chains": 9_406_354}
for name, n in expected.items():
    got = len(pd.read_parquet(CLEAN / name, columns=["date"]))
    print(f"{name:18s} saved {got:>10,}   expected {n:>10,}   {'OK' if got == n else 'MISMATCH'}")