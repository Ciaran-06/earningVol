import pandas as pd

from earning_vol.io import load_clean
from earning_vol.config import DERIVED

prices = load_clean("stock_prices", columns=["ticker", "company", "date", "symbol_at_date"])
calendar = load_clean("earning_calendar", columns=["company", "date"])

# ---- 1. First price date vs first calendar event, per company ----
coverage = pd.concat([
    prices.groupby("company")["date"].min().rename("first_price"),
    calendar.groupby("company")["date"].min().rename("first_event"),
    calendar.groupby("company").size().rename("n_events"),
], axis=1, join="inner")

coverage["gap_days"] = (coverage["first_event"] - coverage["first_price"]).dt.days

# ---- 2. Flag companies whose calendar starts > 1 year after their prices ----
flagged = coverage[coverage["gap_days"] > 365].copy()
flagged["est_missing"] = (flagged["gap_days"] / 365.25 * 4).round().astype(int)

# ---- 3. Old symbols used before the calendar starts ----
old = prices.merge(flagged[["first_event"]], left_on="company", right_index=True)
old = old[(old["date"] < old["first_event"]) & (old["symbol_at_date"] != old["company"])]
old_symbols = old.groupby("company")["symbol_at_date"].agg(lambda s: ", ".join(sorted(s.dropna().unique())))

flagged = flagged.join(old_symbols.rename("old_symbols"))
flagged["old_symbols"] = flagged["old_symbols"].fillna("")
flagged = flagged.sort_values("est_missing", ascending=False)

# ---- 4. Summary ----
renamed = flagged[flagged["old_symbols"] != ""]
no_old = flagged[flagged["old_symbols"] == ""]

print("companies checked:            ", len(coverage))
print("flagged (calendar starts late):", len(flagged))
print("  with old symbols (renames):  ", len(renamed), " est. missing events:", renamed["est_missing"].sum())
print("  no old symbol (other gap):   ", len(no_old), " est. missing events:", no_old["est_missing"].sum())

print("\n=== Renames ===")
print(renamed[["first_price", "first_event", "n_events", "est_missing", "old_symbols"]].to_string())

print("\n=== Gaps with no old symbol ===")
print(no_old[["first_price", "first_event", "n_events", "est_missing"]].to_string())

print("\nMETA:", flagged.loc["META", "old_symbols"] if "META" in flagged.index else "not flagged")

# ---- 5. Save the re-request list: one row per (old symbol, company) ----
rerequest = (renamed["old_symbols"].str.split(", ").explode()
             .rename("old_symbol").reset_index())
out = DERIVED / "manifest" / "calendar_rerequest.csv"
rerequest.to_csv(out, index=False)
print(f"\nsaved {len(rerequest)} symbols to re-request -> {out}")