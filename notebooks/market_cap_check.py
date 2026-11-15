import pandas as pd
from earning_vol.io import load_derived

ev = load_derived("events")
ev["year"] = ev["report_date"].dt.year

# ---- 1. Which input is missing? ----
print("events:                       ", len(ev))
print("NaN market_cap:               ", ev["market_cap"].isna().sum())
print("NaN unadjusted_close_entry:   ", ev["unadjusted_close_entry"].isna().sum())
print("NaN market_cap_corr:          ", ev["market_cap_corr"].isna().sum())

# ---- 2. Where (which years) are they missing? ----
by_year = ev.groupby("year").agg(
    events=("company", "size"),
    missing_cap=("market_cap", lambda s: s.isna().sum()),
    missing_unadj=("unadjusted_close_entry", lambda s: s.isna().sum()),
)
by_year["share_missing"] = (by_year["missing_cap"] / by_year["events"]).round(3)
print("\n", by_year.to_string())

# ---- 3. Spot checks: the correction factor should be 56, 10 and 1 ----
ev["factor"] = (ev["market_cap_corr"] / ev["market_cap"]).round(2)
cols = ["company", "report_date", "market_cap", "market_cap_corr", "factor"]

aapl_2004 = ev[(ev["company"] == "AAPL") & (ev["year"] == 2004)].head(1)
nvda_2023 = ev[(ev["company"] == "NVDA") & (ev["report_date"] == "2023-05-24")]
recent = ev[(ev["year"] == 2026) & ev["market_cap"].notna()].head(3)

print("\nAAPL 2004 (expect factor 56, corrected ~8.7e9):")
print(aapl_2004[cols].to_string(index=False))
print("\nNVDA 2023-05-24 (expect factor 10):")
print(nvda_2023[cols].to_string(index=False))
print("\n2026 events (expect factor 1):")
print(recent[cols].to_string(index=False))

all_missing = ev.groupby("company")["market_cap"].apply(lambda s: s.isna().all())
print("\ncompanies with NO market cap on any event:", all_missing.sum(), "of", len(all_missing))
print(all_missing[all_missing].index.tolist())


