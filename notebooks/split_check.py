import duckdb
from earning_vol.config import RAW

nvda = duckdb.sql(f"""
    SELECT date::DATE AS date, open, high, low, close, unadjusted_close
    FROM read_parquet('{RAW.as_posix()}/equities_eod_stock-prices/NVDA/*.parquet')
    WHERE date::DATE BETWEEN '2021-07-13' AND '2021-07-27'
    ORDER BY date
""").df()

print(nvda)