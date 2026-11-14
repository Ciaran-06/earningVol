import pandas as pd
from earning_vol.io import load_derived

ev = load_derived("events")
ch = ev[ev["has_chains"]]

# 1. which years are missing chains?
miss = ch[ch["straddle_status"] == "no chain on entry day"]
print(miss["report_date"].dt.year.value_counts().sort_index().to_string())

# 2. the NVDA blowout, entry and exit
cols = ["straddle_status", "expiry", "strike", "spot", "implied_move",
        "straddle_bid", "straddle_ask", "exit_bid", "exit_mid", "exit_ask", "exit_spot"]
print(ev[(ev["company"] == "NVDA") & (ev["report_date"] == "2023-05-24")][cols].T)

# 3. usable events for the kill test vs the holdout
ok = ch[ch["straddle_status"] == "ok"]
print(ok["is_holdout"].value_counts())
print("median implied move:", ok["implied_move"].median().round(4))
print("median entry spread, % of mid:",
      ((ok["straddle_ask"] - ok["straddle_bid"]) / ok["straddle_mid"]).median().round(3))