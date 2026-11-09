# DATA.md — data dictionary and known gaps

Last updated: 2026-11-09. Built from `scripts/01_manifest.py`; rerun the manifest after every download and update this file.

## Sources

| Source | What | Where |
|---|---|---|
| IVolatility REST API (end-of-day) | prices, implied vol, historical vol, option chains, earnings calendars | `DATA_ROOT/ivol_data/` |
| Databento | NVDA minute-level options BBO, 2025 | separate folder, not part of `ivol_data` |
| hanshof/sp500_constituents (GitHub) | daily S&P 500 membership history | `sp500_former_members.csv` (409 members that left since 2004) |
| Wikipedia | current S&P 500 members | `sp500_universe.csv` |

Downloaded with `download.py` (free trial runs 2026-11-04 and 2026-11-05). Next download on the paid plan: 2026-11-11, 17,053 jobs planned (earnings chains, SPX 2024–26, 141 renamed-ticker re-requests, earnings chains 2010–14, ivs-by-delta).

## Layout and file naming

```
DATA_ROOT/
├── ivol_data/equities_eod_<dataset>/<ticker>/<file>   raw downloads, never edited
└── ev_data/manifest/{files,schemas}.parquet           built by scripts/01_manifest.py
```

- Date-range chunks: `<from>_<to>.<status>` e.g. `2004-01-01_2008-12-31.parquet`
- Option chains: `<trade_date>_<C|P>.<status>` e.g. `2015-01-02_C.parquet`

| Status | Meaning |
|---|---|
| `.parquet` | data |
| `.empty` | API returned 0 rows (genuinely no data, *or* a renamed ticker; see gaps) |
| `.renamed` / `.notfound` | API said the symbol was renamed / not found (written by the new `download.py` only) |
| `.csv.gz` | fallback if a parquet write failed (none so far) |
| `.tmp` | interrupted write (none so far) |

## Manifest (2026-11-09)

| Dataset | Tickers | Parquet | Empty | Rows | First | Last |
|---|---|---|---|---|---|---|
| history-earnings-calendar | 906 | 659 | 247 | 47,641 | 2004-01-06 | 2026-11-03 |
| hv | 536 | 2,459 | 221 | 2,712,843 | 2004-01-02 | 2026-11-03 |
| ivs | 3 | 68 | 1 | 5,739,136 | 2004-01-02 | 2026-11-03 |
| ivs-by-delta | 7 | 84 | 1 | 6,311,182 | 2004-01-02 | 2026-11-03 |
| ivx | 939 | 4,136 | 484 | 3,474,028 | 2004-01-02 | 2026-11-03 |
| stock-opts-by-param | 2 | 9,612 | 204 | 27,573,626 | 2004-01-02 | 2025-12-31 |
| stock-prices | 939 | 3,251 | 415 | 3,563,937 | 2004-01-02 | 2026-11-03 |
| **Total** | | **20,269** | **1,573** | **49,422,393** | | |

Flag results: 0 zero-row files, 0 unreadable files, 0 bad dates, 0 leftover `.tmp` files, 0 files with dates outside their name's range, 0 chain files containing the wrong day. Schema variants: 95 (calendars), 19 (hv), 2 (chains), all harmless (see schema notes).

## Datasets

All date columns are stored as **text** and must be cast to dates.

### stock-prices: `/equities/eod/stock-prices`
- 939 tickers (current S&P members, former members within ±1 year of their membership window, ETFs); 5-year chunks, 2004-01-01 → 2026-11-03
- Date column: `date`
- Columns: `open`, `high`, `low`, `close`, `unadjusted_close`, `bid`, `ask`, `bid_size`, `ask_size`, `volume`, `exchange`, `symbol`, `record_no`
- **Split-adjusted:** `open`/`high`/`low`/`close` are adjusted for all later splits; `unadjusted_close` is the actual traded price. Verified on NVDA 2021-07-13: `unadjusted_close / close = 40` (= 4 × 10, both splits) and `low ≤ close ≤ high`.
  - **TODO:** confirm the overnight ratio `open_t / close_{t-1} ≈ 1` across the split dates 2021-07-20 and 2024-06-10.
- Realised vol uses the adjusted prices. Option moneyness uses `unadjusted_close` (strikes are unadjusted).

### ivx: `/equities/eod/ivx`
- 939 tickers; mostly 5-year chunks, some tickers in yearly chunks (separate download runs, e.g. META)
- Date column: `date`
- Columns: `<T>d IV Call`, `<T>d IV Put`, `<T>d IV Mean` for T = 7, 14, 21, 30, 60, 90, 120, 150, 180, 270, 360, 720, 1080; plus `price`, `exchange`, `symbol`, `record_no`
- Full implied-vol term structure; short-tenor IV rises into earnings.

### hv: `/equities/eod/hv`
- 536 tickers: **current members and ETFs only (survivorship-biased)**; 5-year chunks
- Date column: `date`
- Columns: `<T>d HV` for T = 10, 20, 30, 60, 90, 120, 150, 180; plus `price`, `exchange`, `symbol`, `record_no`
- Long-window HV columns are entirely null for tickers with short histories.
- Use only as a cross-check; compute realised vol ourselves from `stock-prices`.

### ivs: `/equities/eod/ivs`
- NVDA, SPX, SPY; yearly chunks
- Date column: `date`
- Columns: `Call/Put`, `IV`, `delta`, `strike`, `out-of-the-money %`, `period`, `exchange`, `symbol`, `record_no`

### ivs-by-delta: `/equities/eod/ivs-by-delta`
- 7 tickers incl. AAPL, IWM, MSFT, NVDA, QQQ; 5-year chunks. **MSFT only 2004–2008** (cut off by the trial limit)
- Date column: `date`
- Columns: `delta`, `iv`, `moneyness`, `period`, `exchange`, `symbol`, `record_no`

### stock-opts-by-param: `/equities/eod/stock-opts-by-param` (option chains)
- **NVDA:** daily, 2015-01-02 → 2025-12-31. 102 `.empty` files per side, all market holidays.
- **SPX:** weekly (nearest Wednesday) 2004–2018, daily 2019-01-02 → 2023-12-27
- One file per trade date per side (calls and puts are separate requests). Request filter: DTE 0–400, moneyness ±50%.
- Date column: `c_date`
- Columns: `Bid`, `Ask`, `price`, `price_open`, `price_high`, `price_low`, `iv`, `preiv`, `delta`, `gamma`, `theta`, `vega`, `rho`, `dte`, `expiration_date`, `price_strike`, `calc_OTM`, `underlying_price`, `openinterest`, `volume`, `option_id`, `option_symbol`, `stocks_id`, `is_settlement`, `call_put`
- **`preiv` vs `iv`** (confirmed with IVolatility):
  - `preiv` = IV solved from that row's own option price; `-1` if it could not be calculated (no usable quote).
  - `iv` = `preiv` where available, otherwise **interpolated** across strikes and expiries.
  - Rules: use `preiv` for trades and implied moves (an interpolated IV is not a tradeable price); convert `-1` to null in cleaning; exclude rows with `preiv = -1` from backtest fills.

### history-earnings-calendar: `/equities/eod/history-earnings-calendar`
- 906 tickers; one chunk per ticker, 2004-01-01 → 2026-11-03
- Date column: `earning_date`
- Columns: `earning_date`, `time_of_day_code`, `estimate`, `reported_earning`, `market_cap`, `stock_id`, `symbol`
- No dates beyond 2026-11-03 (the requests ended there), so no scheduled future reports.
- **TODO:** check whether `market_cap` is point-in-time (as of each report) or today's value repeated. If point-in-time, use it to pick the universe as it stood at each date.

## Schema notes

- Effectively **one schema per dataset**. The extra schema variants are only:
  - columns that are entirely null in a file (stored with type `null`)
  - `market_cap` stored as `int64` instead of `double` in 73 calendar files (all whole numbers)
- Cleaning rule: cast every column to its schema-0 type.
- Company ID has two names: `stock_id` (calendars) and `stocks_id` (chains). Rename both to `stock_id`; use it, not the ticker, as the company key (it survives renames). `stock-prices` and `ivx` have no ID column, so they get one via a ticker-to-company map.
- Column names are inconsistent (`Ask` vs `ask`, spaces, `%`). Convert all to `snake_case` in cleaning.

## Lookahead warnings

- `reported_earning` is only known **after** the announcement. Never use it (or any surprise built from it) as a feature for that same event. `estimate` is fine.
- IVolatility's earnings "actual move" fields are the target, not features.
- Event timing depends on `time_of_day_code`: before-open reports move the same day; after-close reports move the next day.

## Known gaps (audit 2026-11-07)

**Not yet downloaded (trial limit hit; planned for 2026-11-11):**
- Earnings-window option chains for the other 47 large caps
- SPX chains 2024 → 2026
- `ivs-by-delta` for ~530 tickers
- NVDA chains 2026

**Ticker renames:**
- 274 `.empty` files were really renamed tickers (`SYMBOL_RENAMED`), listed in `renamed_false_empties.csv`
- 133 are already covered by the new symbol's files (just map them); 141 need re-requesting under the new symbol
- Examples: CTL→LUMN, FB→META, UTX→RTX, PKI→RVTY, SIVB→SIVBQ, FRC→FRCB

**Symbols not found / wrong format:** BRK.B, BRK-B, BF.B (class shares; correct format to be tested 2026-11-11), DALRQ, WNDXQ

**Duplicates to merge:** FLT/CPAY, JEC/J, SYMC & NLOK → GEN, CBS & VIAC → SKYD

**Survivorship bias:**
- `hv` covers current members only
- Earnings calendars are mostly empty for former members
- Bankrupt or failed names (SIVB, FRC, JCP, BBBY) are empty until re-requested

**Selection bias:** the 48-name option-chain universe is *today's* large caps. State this as a limitation, or later pick the universe point-in-time.