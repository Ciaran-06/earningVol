from earning_vol.io import load_derived

ev = load_derived("events")
ok = ev[ev["straddle_status"] == "ok"]

print(ev[(ev["company"] == "NVDA") & (ev["report_date"] == "2023-05-24")][["move_ratio", "y"]])
print("median move_ratio:", ok["move_ratio"].median().round(3))
print("share > 1:        ", (ok["move_ratio"] > 1).mean().round(3))