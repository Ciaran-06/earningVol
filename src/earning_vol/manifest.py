import re
import pandas as pd
from earning_vol.config import RAW

FOLDER_PREFIX = "equities_eod_"
EXTENSIONS = (".parquet", ".csv.gz", ".empty", ".renamed", ".notfound", ".tmp")
CHUNK = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})")
CHAIN = re.compile(r"(\d{4}-\d{2}-\d{2})_([CP])")

def inventory() -> pd.DataFrame:
    rows = []
    exts = sorted(EXTENSIONS, key=len, reverse=True)

    for p in RAW.rglob("*"):
        if not p.is_file():
            continue
        row = {
            "dataset": p.parent.parent.name.removeprefix(FOLDER_PREFIX),
            "ticker": p.parent.name,
            "file": p.name,
            "status": "unknown",
            "size_bytes": p.stat().st_size,
            "path": p.as_posix(),
        }

        # TODO 1
        stem = None
        for ext in exts:
            if p.name.endswith(ext):
                row["status"] = ext[1:]          # ".parquet" -> "parquet"
                stem = p.name[: -len(ext)]       # plain string, works for multi-part exts
                break

        # TODO 2 (only if we recognised the extension)
        if stem is not None:
            if m := CHUNK.fullmatch(stem):
                row["chunk_start"], row["chunk_end"] = m.group(1), m.group(2)
            elif m := CHAIN.fullmatch(stem):
                row["trade_date"], row["cp"] = m.group(1), m.group(2)
            else:
                row["status"] = "unparsed"

        rows.append(row)
    return pd.DataFrame(rows)
