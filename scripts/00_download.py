r"""
download.py: IVolatility Builder-plan pull (budget-guarded, resumable)

PowerShell:
    $env:IVOL_API_KEY="your_key"
    python .\download.py --dry-run          # NO API calls: shows the job plan and which groups fit the budget
    python .\download.py --test             # ~6 calls: checks rename handling, class-share symbols, 2024 SPX chain
    python .\download.py *> console4.txt    # full run; rerun anytime, finished chunks are skipped

Changes from the trial version:
  - request_count.json is counted per billing cycle (resets on BILLING_DAY), and also tracks rows downloaded
  - jobs run in PRIORITY order (earnings chains first), so a budget cut drops the least important work
  - SYMBOL_RENAMED / SYMBOL_NOT_FOUND responses are saved as .renamed / .notfound markers, not .empty,
    and renamed chunks are re-requested under the new symbol automatically on the next run
  - the 141 known renamed-ticker chunks (renamed_false_empties.csv, next to this script) are re-requested
  - every job is logged with its symbol, params and result, not just failures
  - "(Previously XYZ)" junk is stripped from membership symbols
  - future earnings dates no longer pull in the last trading day by mistake
  - NVDA is included in the earnings jobs (its 2015-2025 files are skipped; 2026 events are new)
"""
import os, sys, io, re, json, time, logging
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import ivolatility as ivol

DRY = "--dry-run" in sys.argv
TEST = "--test" in sys.argv
if not DRY:
    ivol.setLoginParams(apiKey=os.environ["IVOL_API_KEY"])

OUT, START, END = Path("ivol_data"), "2004-01-01", "2026-11-03"
MIN_GAP = 1.1          # seconds between calls (limit is 1/s)
BUDGET = 19_000        # calls per billing cycle; plan allows 20,000, keep a margin
BILLING_DAY = 11       # day of the month the paid plan renews
REQ_PER_CALL = 1       # after --test, compare your account usage page with request_count.json; raise if higher

# Job groups, most important first. Delete a name to skip that group.
#   earn     : option chains around each earnings report since EARN_SINCE (the backtest needs these)
#   spx      : SPX chains, weekly 2004-2018, daily 2019+ (2024-2026 still missing)
#   remap    : chunks that came back empty because the ticker was renamed / uses another symbol format
#   removed  : former S&P members' IVX, prices and earnings calendars (already done, kept for completeness)
#   earn_ext : earnings chains EARN_EXT_SINCE to EARN_SINCE (more events = more statistical power)
#   skew     : ivs-by-delta for every ticker with HV data (nice-to-have features)
PRIORITY = ["earn", "spx", "remap", "removed", "earn_ext", "skew"]
EARN_SINCE, EARN_EXT_SINCE = "2015-01-01", "2010-01-01"

RENAMES_CSV = Path("renamed_false_empties.csv")
# Fill in after --test shows which form IVolatility accepts, e.g. {"BRK.B": "BRK/B", "BRK-B": "BRK/B", "BF.B": "BF/B"}
SYMBOL_FIX = {}

OPTS = "/equities/eod/stock-opts-by-param"
CHAIN = dict(dteFrom=0, dteTo=400, moneynessFrom=-50, moneynessTo=50)   # wide is free if the plan limits calls, not rows
SYMBOL_PARAM = {"/equities/eod/history-earnings-calendar": "symbols"}
MEMBERSHIP_URLS = [   # daily S&P 500 membership since 1996 (open-source mirrors)
    "https://raw.githubusercontent.com/hanshof/sp500_constituents/master/sp_500_historical_components.csv",
    "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes.csv",
]
STOCKS = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","AMD","NFLX","JPM","BAC","GS","MS",
          "C","WFC","V","MA","XOM","CVX","COP","UNH","JNJ","PFE","MRK","LLY","ABBV","WMT","COST","HD",
          "MCD","NKE","SBUX","KO","PEP","PG","DIS","BA","CAT","GE","F","GM","INTC","CSCO","ORCL",
          "IBM","QCOM","T","VZ"]

logging.basicConfig(filename="ivol_builder.log", level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(); log.addHandler(logging.StreamHandler())

# ---------- catch the library's SYMBOL_* notices (it logs them, then returns 0 rows) ----------
NOTICE = re.compile(r"(SYMBOL_[A-Z_]+) - (.+)")
RENAME = re.compile(r"(\S+) in \w+ now trades as (\S+) \(stockID=(\d+)\)")

class SymbolNotices(logging.Handler):
    def __init__(self):
        super().__init__(); self.hits = []
    def emit(self, record):
        m = NOTICE.search(record.getMessage())
        if m:
            self.hits.append((m.group(1), m.group(2)))

notice = SymbolNotices()
log.addHandler(notice)

class Stop(Exception):
    pass

# ---------- call counter, per billing cycle ----------
def cycle_key(now=None):
    t = pd.Timestamp(now or pd.Timestamp.now()).normalize()
    if t.day < BILLING_DAY:
        t = t - pd.DateOffset(months=1)
    return f"{t:%Y-%m}-{BILLING_DAY:02d}"

COUNT_FILE = Path("request_count.json")
CYCLE = cycle_key()
state = json.loads(COUNT_FILE.read_text()) if COUNT_FILE.exists() else {}
if state.get("cycle") != CYCLE:          # new cycle, or the old trial-format file: start from zero
    if state:
        log.info(f"billing cycle {CYCLE}: counter reset (previous: {state})")
    state = {"cycle": CYCLE, "calls": 0, "rows": 0}

def save_state():
    COUNT_FILE.write_text(json.dumps(state))

last = 0.0

def fetch(ep, kw):
    global last
    fn = ivol.setMethod(ep)
    for attempt in range(4):
        if state["calls"] + REQ_PER_CALL > BUDGET:
            raise Stop(f"budget reached ({state['calls']} calls this cycle)")
        time.sleep(max(0, MIN_GAP - (time.time() - last))); last = time.time()
        state["calls"] += REQ_PER_CALL
        save_state()
        try:
            df = fn(**kw)
            if df is not None and not isinstance(df, str):
                state["rows"] += len(df); save_state()
            return df
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code == 403:
                raise Stop(f"403 from API: {e}")
            log.warning(f"{ep} {kw} try {attempt+1}: {e}")
            if code and 400 <= code < 500 and code != 429:   # bad request: don't retry
                return "FAILED"
            time.sleep(min(120, 5 * 2 ** attempt))
    return "FAILED"

def ok(df):
    return not isinstance(df, str) and df is not None and len(df) > 0

# ---------- helpers ----------
def trading_days():                       # real trading calendar from your SPY prices
    fs = list((OUT / "equities_eod_stock-prices" / "SPY").glob("*.parquet"))
    d = pd.concat(pd.read_parquet(f, columns=["date"]) for f in fs)["date"]
    return pd.DatetimeIndex(sorted(pd.to_datetime(d).unique()))

def weekly(td, start, end):               # one day per week, closest to Wednesday
    s = td[(td >= start) & (td <= end)]
    df = pd.DataFrame({"d": s, "wk": s.to_period("W-FRI"), "dist": np.abs(s.day_of_week - 2)})
    return list(df.sort_values("dist").groupby("wk")["d"].first().sort_values())

def years(start, end, n):
    s, e, out = pd.Timestamp(start), pd.Timestamp(end), []
    while s <= e:
        t = min(s + pd.DateOffset(years=n) - pd.Timedelta(days=1), e)
        out.append({"from_": f"{s:%Y-%m-%d}", "to": f"{t:%Y-%m-%d}"})
        s = t + pd.Timedelta(days=1)
    return out

def clean_sym(s):                         # "RVTY (Previously PKI)" -> "RVTY"
    return s.astype(str).str.replace(r"\s*\(.*?\)\s*$", "", regex=True).str.strip()

def load_former_members():
    """Former S&P 500 members (left since 2004) with first/last date in the index."""
    cache = Path("sp500_former_members.csv")
    if not cache.exists():
        raw = None
        for url in MEMBERSHIP_URLS:
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
                r.raise_for_status()
                raw = pd.read_csv(io.StringIO(r.text))
                log.info(f"membership history from {url}")
                break
            except Exception as e:
                log.warning(f"membership source failed ({url}): {e}")
        if raw is None:
            raise RuntimeError("Could not download S&P 500 membership history")
        dcol = raw.columns[0]
        tcol = next((c for c in raw.columns if "ticker" in str(c).lower()), raw.columns[1])
        s = raw[[dcol, tcol]].copy()
        s[dcol] = pd.to_datetime(s[dcol], errors="coerce")
        s = s.dropna(subset=[dcol])
        s[tcol] = s[tcol].astype(str).str.split(",")
        s = s.explode(tcol)
        s["symbol"] = s[tcol].str.strip().str.replace(r"-\d{6}$", "", regex=True)  # fja05680 suffixes
        s = s[s["symbol"].str.len() > 0]
        m = s.groupby("symbol")[dcol].agg(["min", "max"]).reset_index()
        m.columns = ["symbol", "first", "removed"]
        m = m[(m["removed"] < m["removed"].max()) & (m["removed"] >= pd.Timestamp(START))]
        m.to_csv(cache, index=False)
        log.info(f"saved {len(m)} former members (left the index {START} or later)")
    df = pd.read_csv(cache)
    for c in ("first", "removed"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["symbol"] = clean_sym(df["symbol"])
    return df.groupby("symbol", as_index=False).agg(first=("first", "min"), removed=("removed", "max"))

def earnings_events(sym, since, until=None):
    d = OUT / "equities_eod_history-earnings-calendar" / sym
    fs = [f for f in d.glob("*") if f.name.endswith((".parquet", ".csv.gz"))] if d.exists() else []
    if not fs:
        return []
    df = pd.concat(pd.read_parquet(f) if f.name.endswith(".parquet") else pd.read_csv(f) for f in fs)
    df["d"] = pd.to_datetime(df["earning_date"], errors="coerce")
    df = df.dropna(subset=["d"])
    df = df[(df["d"] >= since) & (df["d"] <= END)]          # drop scheduled future reports
    if until:
        df = df[df["d"] < until]
    return list(zip(df["d"], df["time_of_day_code"].astype(str).str.upper().str.strip()))

def event_days(td, d, code):
    """Last close before the report and first close after it."""
    i = td.searchsorted(pd.Timestamp(d))          # first trading day on/after the report date
    if code.startswith("B") or any(k in code for k in ("BMO", "BEFORE", "PRE")):
        js = (i - 1, i)                            # before open: day before, day of
    elif code.startswith("A") or any(k in code for k in ("AMC", "AFTER", "POST")):
        js = (i, i + 1)                            # after close: day of, day after
    else:
        js = (i - 1, i, i + 1)                     # unknown timing: take all three
    return {td[j] for j in js if 0 <= j < len(td)}

def safe_dir(sym):                        # "BRK/B" -> "BRK_B" so it can't create nested folders
    return re.sub(r"[^\w.\-]", "_", sym)

def out_path(ep, sym, p):
    key = "_".join(str(p[k]) for k in ("tradeDate", "from_", "to", "cp") if k in p)
    return OUT / ep.strip("/").replace("/", "_") / safe_dir(sym or "all") / key

DONE = (".parquet", ".csv.gz", ".empty", ".renamed", ".notfound")

def is_done(base):
    return any(base.with_suffix(s).exists() for s in DONE)

def save(df, base, hits=()):
    base.parent.mkdir(parents=True, exist_ok=True)
    if ok(df):
        tmp = base.with_suffix(".tmp")
        try:
            df.to_parquet(tmp, index=False); tmp.replace(base.with_suffix(".parquet")); return "parquet"
        except Exception:
            df.to_csv(tmp, index=False, compression="gzip"); tmp.replace(base.with_suffix(".csv.gz")); return "csv.gz"
    for code, msg in reversed(hits):
        m = RENAME.search(msg)
        if code == "SYMBOL_RENAMED" and m:
            base.with_suffix(".renamed").write_text(json.dumps(
                {"old": m.group(1), "new": m.group(2), "stock_id": int(m.group(3)), "msg": msg}))
            return f"renamed -> {m.group(2)}"
        if code == "SYMBOL_NOT_FOUND":
            base.with_suffix(".notfound").write_text(json.dumps({"msg": msg}))
            return "notfound"
    base.with_suffix(".empty").touch(); return "empty"

def params_from_key(key):                 # file name -> request params
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", key)
    if m:
        return {"from_": m.group(1), "to": m.group(2)}
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})_([CP])", key)
    if m:
        return {"tradeDate": m.group(1), **CHAIN, "cp": m.group(2)}
    return None

# ---------- test probes ----------
if TEST:
    probes = [
        ("rename caught (CTL ivx)",     "/equities/eod/ivx",          {"symbol": "CTL",  "from_": "2008-01-02", "to": "2008-01-31"}),
        ("old history via LUMN",        "/equities/eod/stock-prices", {"symbol": "LUMN", "from_": "2008-01-02", "to": "2008-01-31"}),
        ("SPX chain 2024 (paid data)",  OPTS, {"symbol": "SPX", "tradeDate": "2024-01-02", "cp": "C", **CHAIN}),
    ] + [(f"class share '{s}'", "/equities/eod/stock-prices", {"symbol": s, "from_": "2024-01-02", "to": "2024-01-31"})
         for s in ("BRK/B", "BRK B", "BRKB")]
    try:
        for label, ep, kw in probes:
            notice.hits.clear()
            df = fetch(ep, kw)
            hits = " | ".join(f"{c}: {m[:80]}" for c, m in notice.hits)
            print(f"{label:28s} -> {df.shape if ok(df) else 'EMPTY/FAILED'}  {hits}")
    except Stop as e:
        print("STOPPED:", e); sys.exit(1)
    print(f"calls counted this cycle: {state['calls']}  <- compare with your IVolatility account usage page")
    codes = Counter(c for s in STOCKS[:10] for _, c in earnings_events(s, EARN_SINCE))
    print("earnings time_of_day_code values:", dict(codes))

# ---------- job groups ----------
SIDES = [{"cp": "C"}, {"cp": "P"}]       # API requires cp, so calls and puts are separate requests
td = trading_days()
current = set(clean_sym(pd.read_csv("sp500_universe.csv")["symbol"]))

def earn_jobs(tag, since, until=None):
    jobs = []
    for sym in STOCKS:
        days_ = set()
        for d, code in earnings_events(sym, since, until):
            days_ |= event_days(td, d, code)
        jobs += [(tag, OPTS, sym, {"tradeDate": f"{d:%Y-%m-%d}", **CHAIN, **side})
                 for d in sorted(days_) for side in SIDES]
    return jobs

def spx_jobs():
    return [("spx", OPTS, "SPX", {"tradeDate": f"{d:%Y-%m-%d}", **CHAIN, **side})
            for d in weekly(td, "2004-01-01", "2018-12-31") + list(td[td >= "2019-01-01"]) for side in SIDES]

def remap_jobs():
    pairs = []                            # (dataset folder, chunk key, symbol to query)
    if RENAMES_CSV.exists():
        r = pd.read_csv(RENAMES_CSV)
        r = r[r["action"].str.startswith("re-request")]
        pairs += [(Path(f).parent.parent.name, Path(f).stem, new) for f, new in zip(r["empty_file"], r["new_symbol"])]
    else:
        log.warning(f"{RENAMES_CSV} not found next to the script: skipping the known renamed-ticker re-requests")
    for old, new in SYMBOL_FIX.items():
        pairs += [(f.parent.parent.name, f.stem, new) for f in OUT.glob(f"*/{old}/*") if f.suffix in (".empty", ".notfound")]
    for f in OUT.glob("*/*/*.renamed"):
        pairs.append((f.parent.parent.name, f.stem, json.loads(f.read_text())["new"]))
    jobs = []
    for ds, key, new in pairs:
        p = params_from_key(key)
        if p:
            jobs.append(("remap", "/" + ds.replace("_", "/"), new, p))
    return jobs

def removed_jobs():                       # IVX + prices from 1y before joining to 1y after leaving, plus earnings
    rem = load_former_members()
    rem = rem[~rem["symbol"].isin(current | set(STOCKS))]
    jobs = []
    for ep in ["/equities/eod/ivx", "/equities/eod/stock-prices"]:
        for sym, f, r in zip(rem["symbol"], rem["first"], rem["removed"]):
            lo, hi = f - pd.Timedelta(days=365), r + pd.Timedelta(days=365)
            jobs += [("removed", ep, sym, c) for c in years(START, END, 5)
                     if pd.Timestamp(c["from_"]) <= hi and pd.Timestamp(c["to"]) >= lo]
    jobs += [("removed", "/equities/eod/history-earnings-calendar", s, c)
             for s in rem["symbol"] for c in years(START, END, 25)]
    return jobs

def skew_jobs():                          # every ticker that has real HV data (current members + ETFs)
    hv = OUT / "equities_eod_hv"
    syms = sorted(p.name for p in hv.iterdir() if p.is_dir() and any(p.glob("*.parquet"))) if hv.exists() else sorted(current)
    return [("skew", "/equities/eod/ivs-by-delta", s, c) for s in syms for c in years(START, END, 5)]

BUILDERS = {"earn": lambda: earn_jobs("earn", EARN_SINCE), "spx": spx_jobs, "remap": remap_jobs,
            "removed": removed_jobs, "earn_ext": lambda: earn_jobs("earn_ext", EARN_EXT_SINCE, EARN_SINCE),
            "skew": skew_jobs}
JOBS = [j for g in PRIORITY for j in BUILDERS[g]()]

todo, seen = [], set()
for j in JOBS:                            # skip finished chunks and duplicates (first = higher priority wins)
    b = out_path(j[1], j[2], j[3])
    if b in seen or is_done(b):
        continue
    seen.add(b); todo.append(j)

room = max(0, (BUDGET - state["calls"]) // REQ_PER_CALL)
log.info(f"cycle {CYCLE}: {state['calls']} calls used, room for {room} more | {len(todo)} jobs to do")
cum = 0
for g in PRIORITY:
    k = sum(1 for j in todo if j[0] == g)
    fit = "fits" if cum + k <= room else ("partly fits" if cum < room else "CUT (over budget)")
    cum += k
    log.info(f"  {g:9s} {k:6d} jobs   cumulative {cum:6d}   {fit}")
if TEST or DRY:
    sys.exit(0)

# ---------- run ----------
n = 0
try:
    for tag, ep, sym, p in todo:
        base = out_path(ep, sym, p)
        notice.hits.clear()
        df = fetch(ep, {**p, SYMBOL_PARAM.get(ep, "symbol"): sym})
        hits = list(notice.hits)
        if isinstance(df, str):
            log.error(f"FAILED [{tag}] {ep} {sym} {p}"); continue
        kind = save(df, base, hits)
        log.info(f"OK [{tag}] {ep} {sym} {p} -> {kind}, {len(df) if ok(df) else 0} rows")
        n += 1
        if n % 100 == 0:
            log.info(f"{n}/{len(todo)} new [{tag}] | calls used {state['calls']} | rows {state['rows']:,}")
except Stop as e:
    log.error(f"Stopped: {e}")
log.info(f"Done: {n} new files, {state['calls']} calls this cycle, {state['rows']:,} rows.")