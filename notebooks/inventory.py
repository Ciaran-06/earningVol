
from earning_vol.manifest import inventory

df = inventory()
print(df.groupby(["dataset", "status"]).size().unstack(fill_value=0))