from earning_vol.io import load_derived

df = load_derived("events")
print(df.head(5))