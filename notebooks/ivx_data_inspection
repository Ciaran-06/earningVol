from earning_vol.clean import clean_ivx ,load_raw

df = load_raw("ivx")
#print(df.min(axis=0))
#print(f"NaN's {df.isna().sum()}")
#print(df.head())

def ivx_rename_helper(name):
    n = name.split()
    tenor = n[0]
    type  = n[2]
   # print(f"iv_{tenor}_{type}")


ivx_rename_helper("1080d IV Mean")

print(df.describe().T)

clean_ivx(df)

