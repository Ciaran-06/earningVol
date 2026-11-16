"""Checks and results for the kill test and the cost diagnostics.

Run from the repo root:  uv run python notebooks/strat_tester.py
"""
import pandas as pd

from earning_vol.io import load_derived
from earning_vol.strategy import (
    kill_sample, straddle_pnl, rule_pnl, summarise, linear_oos,
    mid_pnl, spreads, cost_table,
)


def rules_table(sample: pd.DataFrame) -> pd.DataFrame:
    """One row per rule: n, mean, std, t."""
    rules = rule_pnl(sample)
    return pd.DataFrame([summarise(p) for p in rules.values()], index=list(rules.keys()))


events = load_derived("events")
sample = kill_sample(events)
sample_2013 = sample[sample["report_date"] >= "2013-01-01"]

sell = straddle_pnl(sample, "sell")
buy = straddle_pnl(sample, "buy")
rules = rule_pnl(sample)
spr = spreads(sample)
nvda_idx = sample[(sample["company"] == "NVDA") & (sample["report_date"] == "2023-05-24")].index[0]

# ================================================================= CHECKS
print("\n================ Checks ================")

print("-- summarise on [1, 2, 3] (expect n 3, mean 2, std 1, t 3.464)")
print(summarise(pd.Series([1, 2, 3])))

print("\n-- NVDA 2023-05-24 (expect buy 2.362, sell -2.480)")
print("buy:                        ", buy.loc[nvda_idx])
print("sell:                       ", sell.loc[nvda_idx])

print("\n-- rule sizes (expect 2,620, and sell_rich + buy_cheap = 2,620)")
print("always_sell:                ", len(rules["always_sell"]))
print("sell_rich + buy_cheap:      ", len(rules["sell_rich"]) + len(rules["buy_cheap"]))
print("NVDA in sell_rich:          ", nvda_idx in rules["sell_rich"].index)   # expect True
print("NVDA in buy_cheap:          ", nvda_idx in rules["buy_cheap"].index)   # expect False

print("\n-- cost identities (expect ~0)")
print("max |sell + buy + spreads|: ", (sell + buy + spr["entry_spread"] + spr["exit_spread"]).abs().max())
print("max |mid sell + mid buy|:   ", (mid_pnl(sample, "sell") + mid_pnl(sample, "buy")).abs().max())

print("\n-- NVDA costs (expect mid sell -2.420, entry spread 0.053, exit spread 0.065)")
print("mid sell:                   ", mid_pnl(sample, "sell").loc[nvda_idx])
print("entry spread:               ", spr.loc[nvda_idx, "entry_spread"])
print("exit spread:                ", spr.loc[nvda_idx, "exit_spread"])

print("\n-- 2013 sample (expect n 2,098, first date 2013-01-11)")
print("n:                          ", len(sample_2013))
print("earliest report date:       ", sample_2013["report_date"].min())

# ================================================================= RESULTS
print("\n================ Rules: full sample ================")
print(rules_table(sample).round(4).to_string())

print("\n================ Rules: from 2013-01-01 ================")
print(rules_table(sample_2013).round(4).to_string())

print("\n================ Linear model (train 2010-18, test 2019-23) ================")
for key, value in linear_oos(sample).items():
    print(f"{key:<12}{value}")

print("\n================ Cost diagnostics: full sample ================")
print(cost_table(sample).round(4).to_string())

print("\n================ Cost diagnostics: from 2013-01-01 ================")
print(cost_table(sample_2013).round(4).to_string())