import numpy as np

from earning_vol.io import load_derived

df = load_derived("events")

df = df[df["company"] == "NVDA"]
df = df.sort_values("report_date")
df = df.reset_index(drop=True)

pos = df.index[df["report_date"] == "2023-05-24"][0]
prev_8 = df.iloc[pos -8 : pos]
abs_move_simple = np.abs((prev_8["close_reaction"] / prev_8["close_entry"])-1)
mean = abs_move_simple.mean()
print("Mean:         ",mean)
print("hist_move_8:  ", df.loc[pos, "hist_move_8"])