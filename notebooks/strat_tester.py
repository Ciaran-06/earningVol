import pandas as pd
import numpy as np
from earning_vol.io import load_derived
from earning_vol.strategy import kill_sample, straddle_pnl, rule_pnl, summarise, linear_oos

events = load_derived("events")

sample = kill_sample(events)

sell = straddle_pnl(sample, "sell")
buy = straddle_pnl(sample, "buy")

print("=============Robustness: from 2013-01-01==============")
sample_2013 = sample[sample["report_date"] >= "2013-01-01"]
print("n (from 2013):              ", len(sample_2013))
print("Earliest report date:       ", sample_2013["report_date"].min())

rules_2013 = rule_pnl(sample_2013)
table_2013 = pd.DataFrame(
    [summarise(pnl) for pnl in rules_2013.values()],
    index=list(rules_2013.keys()),
)
print(table_2013.round(4).to_string())

nvda_pos = sample[(sample["company"] == "NVDA") & (sample["report_date"] == "2023-05-24")].index
print("Buy:                        ",buy.loc[nvda_pos].iloc[0])
print("Sell:                       ",sell.loc[nvda_pos].iloc[0])

rules = rule_pnl(sample)
print("Length of Series:           ", len(rules["always_sell"]))
print("Check for Data Loss:        ", len(rules["sell_rich"]) + len(rules["buy_cheap"]))
print("Selected NVDA in sell rich: ", nvda_pos[0] in rules["sell_rich"].index)
print("Selected NVDA in buy cheap: ", nvda_pos[0] in rules["buy_cheap"].index)
print("Math Check:                 ", rules["sell_rich"].loc[nvda_pos[0]])

print("=============Summarise===============")
print("Series Normal [1,2,3]:      ",summarise(pd.Series([1,2,3])))
pnl = rule_pnl(sample)
always_sell = summarise(pnl["always_sell"])
print("Summary of always sell:     ")
print("Always Sell(n):             ",always_sell["n"])
print("Always Sell(mean):          ",always_sell["mean"])
print("Always Sell(std):           ",always_sell["std"])
print("Always Sell(t):             ",always_sell["t"])

print("=====================================")
sell_rich = summarise(pnl["sell_rich"])
print("Summary of sell rich:       ")
print("Sell Rich(n):               ",sell_rich["n"])
print("Sell Rich(mean):            ",sell_rich["mean"])
print("Sell Rich(std):             ",sell_rich["std"])
print("Sell Rich(t):               ",sell_rich["t"])

print("=====================================")
buy_cheap = summarise(pnl["buy_cheap"])
print("Summary of buy cheap:       ")
print("Buy Cheap(n):               ",buy_cheap["n"])
print("Buy Cheap(mean):            ",buy_cheap["mean"])
print("Buy Cheap(std):             ",buy_cheap["std"])
print("Buy Cheap(t):               ",buy_cheap["t"])

print("=============Linear OOS==============")
oos_result = linear_oos(sample)
print("n_train:                    ", oos_result["n_train"])
print("n_test:                     ", oos_result["n_test"])
print("a:                          ", oos_result["a"])
print("b:                          ", oos_result["b"])
print("r2_vs_mean:                 ", oos_result["r2_vs_mean"])
print("r2_vs_zero:                 ", oos_result["r2_vs_zero"])