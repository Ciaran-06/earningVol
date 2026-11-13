import re
import pandas as pd
import pyarrow.parquet as pq
import duckdb as db

from collections import Counter

from earning_vol.config import RAW

FOLDER_PREFIX = "equities_eod_"
DATE_COL = {
    "history-earnings-calendar": "earning_date",
    "hv": "date",
    "ivs": "date",
    "ivs-by-delta": "date",
    "ivx": "date",
    "stock-prices": "date",
    "stock-opts-by-param": "c_date",
}

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

        stem = None
        for ext in exts:
            if p.name.endswith(ext):
                row["status"] = ext[1:]          
                stem = p.name[: -len(ext)]       
                break

        if stem is not None:
            if m := CHUNK.fullmatch(stem):
                row["chunk_start"], row["chunk_end"] = m.group(1), m.group(2)
            elif m := CHAIN.fullmatch(stem):
                row["trade_date"], row["cp"] = m.group(1), m.group(2)
            else:
                row["status"] = "unparsed"

        rows.append(row)
    return pd.DataFrame(rows)

def _fingerprint(path):
    """Sorted (column, type) pairs for one parquet file, plus its row count. Reads the footer only."""
    meta = pq.read_metadata(path)
    pairs = []
    for field in meta.schema.to_arrow_schema():
        t = str(field.type)
        if t == "large_string":          # same data as "string", just bigger offsets
            t = "string"
        pairs.append((field.name, t))
    return tuple(sorted(pairs)), meta.num_rows


def schemas(inv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Read every parquet footer (no data) and group the files by schema.

    Returns
      files   : one row per parquet file -> path, dataset, num_rows, schema_id, error
      summary : one row per (dataset, schema_id, column) -> type, n_files, first_date, last_date
    """
    pq_files = inv[inv["status"] == "parquet"]

    results = []
    for path, dataset in zip(pq_files["path"], pq_files["dataset"]):
        rec = {"path": path, "dataset": dataset, "num_rows": None, "fingerprint": None, "error": None}
        try:
            rec["fingerprint"], rec["num_rows"] = _fingerprint(path)
        except Exception as e:           # corrupt / unreadable file: record it, keep going
            rec["error"] = f"{type(e).__name__}: {e}"
        results.append(rec)
    files = pd.DataFrame(results)
    files["num_rows"] = files["num_rows"].astype("Int64")

    # schema_id per dataset: 0 = most common schema, 1 = next, ...
    files["schema_id"] = pd.array([pd.NA] * len(files), dtype="Int64")
    for _, g in files[files["fingerprint"].notna()].groupby("dataset"):
        ranked = [fp for fp, _ in Counter(g["fingerprint"]).most_common()]
        ids = {fp: i for i, fp in enumerate(ranked)}
        files.loc[g.index, "schema_id"] = [ids[fp] for fp in g["fingerprint"]]

    # date span of each file, from the inventory's parsed file names
    dates = inv.set_index("path").reindex(columns=["chunk_start", "chunk_end", "trade_date"])
    span = pd.DataFrame({
        "first_date": pd.to_datetime(dates["chunk_start"].fillna(dates["trade_date"])),
        "last_date": pd.to_datetime(dates["chunk_end"].fillna(dates["trade_date"])),
    })
    files = files.join(span, on="path")

    # long summary: one row per column of each distinct schema
    rows = []
    for (dataset, sid), g in files[files["fingerprint"].notna()].groupby(["dataset", "schema_id"]):
        for column, dtype in g["fingerprint"].iloc[0]:
            rows.append({"dataset": dataset, "schema_id": sid, "column": column, "type": dtype,
                         "n_files": len(g), "first_date": g["first_date"].min(),
                         "last_date": g["last_date"].max(), "example_path": g["path"].iloc[0]})
    summary = pd.DataFrame(rows)

    files = files.drop(columns=["fingerprint", "first_date", "last_date"])
    return files, summary

def contents(inv: pd.DataFrame) -> pd.DataFrame:
    pq_files = inv[inv["status"] == "parquet"]
    results = []
    for path, dataset in zip(pq_files["path"], pq_files["dataset"]):
        rec = {"path": path, "min_date": None, "max_date": None, "bad_dates": None, "error": None}
        try:
            data = pd.read_parquet(path, columns=[DATE_COL[dataset]])
            dates = pd.to_datetime(data[DATE_COL[dataset]], errors="coerce")
            rec["min_date"] = dates.min()
            rec["max_date"] = dates.max()
            rec["bad_dates"] = int(dates.isna().sum())
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        results.append(rec)

    return pd.DataFrame(results)
