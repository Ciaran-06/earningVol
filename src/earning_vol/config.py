import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]   # config.py → earning_vol → src → repo root
load_dotenv(REPO_ROOT / ".env")

DATA_ROOT = Path(os.environ["DATA_ROOT"])