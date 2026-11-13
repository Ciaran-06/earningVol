"""Project paths and research settings. Import from here; never hard-code paths."""
import os
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

RAW_DATASETS = {
    "stock_prices":     "stock-prices",
    "chains":           "stock-opts-by-param",
    "ivx":              "ivx",
    "ivs_by_delta":     "ivs-by-delta",
    "ivs":              "ivs",
    "hv":               "hv",
    "earning_calendar": "history-earnings-calendar",
}

REPO_ROOT = Path(__file__).resolve().parents[2]   # config.py -> earning_vol -> src -> repo root
load_dotenv(REPO_ROOT / ".env")

try:
    DATA_ROOT = Path(os.environ["DATA_ROOT"])
except KeyError:
    raise KeyError("DATA_ROOT not set: add it to .env in the repo root") from None
if not DATA_ROOT.exists():
    raise FileNotFoundError(f"DATA_ROOT does not exist: {DATA_ROOT} (check .env)")

with open(REPO_ROOT / "configs" / "base.yaml") as f:
    CFG = yaml.safe_load(f)

RAW = DATA_ROOT / CFG["raw_dir"]           # untouched downloads, never written to
DERIVED = DATA_ROOT / CFG["derived_dir"]   # everything the pipeline produces

START = pd.Timestamp(CFG["start"])
END = pd.Timestamp(CFG["end"])
VALIDATION_START = pd.Timestamp(CFG["validation_start"])
HOLDOUT_START = pd.Timestamp(CFG["holdout_start"])

if not (START < VALIDATION_START < HOLDOUT_START < END):
    raise ValueError("dates in base.yaml are out of order")