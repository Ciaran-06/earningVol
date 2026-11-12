# DATA.md — data dictionary, cleaning rules and known gaps

Last updated: 2026-11-12. Rerun `scripts/01_manifest.py` and `scripts/02_clean.py` after every download and update this file.

## Sources

| Source | What | Where |
|---|---|---|
| IVolatility REST API (end-of-day) | prices, implied vol, historical vol, option chains, earnings calendars | `DATA_ROOT/ivol_data/` |
| Databento | NVDA minute-level options BBO, 2025 (plus ~$125 credit, planned: 1-minute stock bars) | separate folder, not part of `ivol_data` |
| hanshof/sp500_constituents (GitHub) | daily S&P 500 membership history | `sp500_former_members.csv` (409 members that left since 2004) |
| Wikipedia | current S&P 500 members | `sp500_universe.csv` |

Downloaded with `scripts/00_download.py` (run from `DATA_ROOT`).
- Free trial runs: 2026-11-04 and 2026-11-05 (6,462 calls; these counted against the first paid month).
- Paid run: 2026-11-11 → 2026-11-12, 13,000 calls, 12,995 new files, 21.8M rows, 0 failures. Stopped at the budget as planned.
- **Still to download after the quota resets:** `earn_ext` 1,496 jobs (2010–14 earnings chains, from MCD onwards) and `skew` 2,649 jobs (`ivs-by-delta`). ~539 calls left this cycle, kept as a margin for fixes.
- IVolatility counts exactly one request per data call; polling and file downloads do not count.

## Layout

```
DATA_ROOT/
├── ivol_data/equities_eod_<dataset>/<ticker>/<file>         raw downloads, never edited
└── ev_data/
    ├── manifest/{files,schemas}.parquet                     scripts/01_manifest.py
    └── clean/
        ├── stock_prices/year=YYYY/*.parquet                 scripts/02_clean.py
        ├── earning_calendar/year=YYYY/*.parquet
        ├── ivx/year=YYYY/*.parquet
        └── chains/ticker=XXX/year=YYYY/*.parquet            split by ticker AND year
```

Raw file names:
- Date-range chunks: `<from>_<to>.<status>` e.g. `2004-01-01_2008-12-31.parquet`
- Option chains: `<trade_date>_<C|P>.<status>` e.g. `2015-01-02_C.parquet`

| Status | Meaning |
|---|---|
| `.parquet` | data |
| `.empty` | API returned 0 rows (genuinely no data, *or* a renamed ticker not yet rechecked) |
| `.renamed` / `.notfound` | API said the symbol was renamed / not found |
| `.csv.gz` | fallback if a parquet write failed (none so far) |
| `.tmp` | interrupted write (none so far) |

Clean files have random names inside each partition folder (normal for partitioned parquet). Read a dataset with `pd.read_parquet(DERIVED / "clean" / name)`; for one ticker's chains add `filters=[("ticker", "=", "NVDA")]`. `ticker` and `year` come back as category columns. `save_clean` deletes before writing (the whole dataset, or only the tickers being saved for chains), so reruns never duplicate data.

## Manifest (2026-11-12, after the paid download)

| Dataset | Tickers | Parquet | Empty | Rows | First | Last |
|---|---|---|---|---|---|---|
| history-earnings-calendar | 931 | 679 | 252 | 48,044 | 2004-01-06 | 2026-11-03 |
| hv | 538 | 2,469 | 221 | 2,724,330 | 2004-01-02 | 2026-11-03 |
| ivs | 3 | 68 | 1 | 5,739,136 | 2004-01-02 | 2026-11-03 |
| ivs-by-delta | 7 | 84 | 1 | 6,311,182 | 2004-01-02 | 2026-11-03 |
| ivx | 964 | 4,202 | 489 | 3,552,737 | 2004-01-02 | 2026-11-03 |
| stock-opts-by-param | 50 | 22,374 | 204 | 49,182,294 | 2004-01-02 | 2026-11-03 |
| stock-prices | 964 | 3,320 | 417 | 3,646,597 | 2004-01-02 | 2026-11-03 |

Flags: 0 zero-row files, 0 unreadable files, 0 bad dates, 0 `.tmp` files, 0 files with dates outside their name's range, 0 chain files containing the wrong day. Schema variants: 105 (calendars), 19 (hv), 2,526 (chains), all handled in cleaning (see schema notes).

The paid download added 25 tickers to prices, `ivx` and the calendars: recovered renames, bankrupt names under their OTC tickers, and the class shares (`BRK_B`, `BF_B`).

## Clean layer (2026-11-12)

| Clean dataset | Rows in | Rows out | Notes |
|---|---|---|---|
| `stock_prices` | 3,646,597 | 3,639,381 | 10 corporate-action days flagged (after adding FRCB to `REAL_MOVES`) |
| `earning_calendar` | 48,044 | 48,035 | 0 duplicates; 27,354 BMO, 20,681 AMC, 0 UNKNOWN |
| `ivx` | 3,552,737 | 3,549,501 | 0 duplicates; 1,528 capped IV cells set to NaN |
| `chains` | 9,406,354 | 9,406,354 | 49 stocks; 0 duplicate contracts; **SPX not cleaned yet** |

Checks after the run: readback counts match for all four; **no symbol appears under two folders on the same date** in prices, `ivx` or the calendar (the BBT recheck did not mix companies).

### Rules applied to every dataset
- Rows from `DROP_TICKERS` are removed (see below).
- Dates are converted from text to real dates; the date column is always called `date`.
- Identity columns come first: `ticker`, `company`, `date`. Rows are sorted by company and date.
- `ticker` = the folder the data came from (the symbol requested from the API, usually the company's **current** ticker). `company` = the identity used for joins and grouping; currently equal to `ticker`, kept separate so folders can be merged later.
- `symbol_at_date` (was `symbol`) = what the company traded as **on that date**. **Never join or group on it**: the same string can mean different companies at different times (see ticker reuse).
- The `filename` and `record_no` columns are dropped.

### Excluded folders: `DROP_TICKERS = {FLT, JEC, PARA}`
- `FLT` and `JEC`: old tickers of FleetCor (now `CPAY`) and Jacobs (now `J`). Their history already sits in the current folders, so keeping them would double-count those companies.
- `PARA`: the folder contains a different company (symbols `VII`, then `BNZI`); the ticker appears to have been reused. Paramount's real history is in `SKYD` (labelled `CBS` in earlier years).

### Ticker renames, reuse and restructurings (found via `symbol_at_date != ticker`)
- **Renames (most cases):** the price is continuous across the symbol switch, so it is the same company. Examples: PKI→RVTY, UTX→RTX, PCLN→BKNG, FLT→CPAY, TASR→AXON, EQR→VMRK, SATS→ECHO, MMC→MRSH.
- **Ticker reuse:** `BBT` was BB&T until 2019 (its history is now in the `TFC` folder); the `BBT` folder holds a different bank (formerly `BHLB`) that took the ticker later.
- **Restructurings:** `DD` (formerly DowDuPont / Dow) and `JCI` (pre-2016 history is Tyco's) change business at the switch. Treat these as structural breaks in vol modelling.
- **Bankrupt / delisted names** are stored under their OTC ticker (e.g. `SIVBQ`, `FRCB`), so `company` is that ticker.

### stock_prices
- Columns: `open`, `high`, `low`, `close`, `unadjusted_close`, `bid`, `ask`, `bid_size`, `ask_size`, `volume`, `exchange`, `symbol_at_date`, `corporate_action`
- Sanity checks (all 0): close ≤ 0, missing close, high < low, close outside [low, high], duplicate (company, date).
- **Split adjustment:** `open`/`high`/`low`/`close` are adjusted for all later splits; `unadjusted_close` is the actual traded price. Verified on NVDA 2021-07-13: `unadjusted_close / close = 40` (= 4 × 10, both splits), and `low ≤ close ≤ high`. The ratio being exactly 40 suggests prices are adjusted for **splits only, not dividends**.
  - **TODO:** confirm the overnight ratio `open_t / close_{t-1} ≈ 1` across 2021-07-20 and 2024-06-10.
- Realised vol uses the adjusted prices. Option moneyness uses `unadjusted_close` (strikes are unadjusted).
- **`corporate_action` flag:** True on days where the symbol changes **and** the absolute log close-to-close move is above 0.1, excluding bankruptcies (new symbol ends in `Q`) and `REAL_MOVES = {FMCC, FNMA, FRCB}`. These days' returns are excluded from realised vol.

| Ticker | Date | Event |
|---|---|---|
| APTV | 2017-12-05 | Delphi spun off Delphi Technologies |
| AXON | 2005-11-25 | ticker became `TASRE` (late-filing suffix); unclear, flagged to be safe |
| DD | 2019-06-03 | DowDuPont split (Corteva spin-off) |
| HWM | 2020-04-01 | Arconic separation |
| KDP | 2018-07-10 | Dr Pepper Snapple ~$104 special dividend (Keurig merger) |
| MDLZ | 2012-10-02 | Kraft spun off Kraft Foods Group |
| MSI | 2011-01-04 | Motorola Mobility spin-off |
| TGNA | 2015-06-29 | Gannett spun off its newspapers |
| TT | 2020-03-02 | Ingersoll-Rand spun off its industrial business |
| WEN | 2008-09-30 | Triarc / Wendy's merger; unclear, flagged to be safe |

  - Rule for unclear cases: flag them. Excluding one real day barely changes realised vol; including a fake 15–40% move creates a large false spike.
  - **Not flagged on purpose (real losses):** bankruptcies (WaMu, Lehman, Ambac, old GM, Kodak, Peabody, SVB → `SIVBQ`, …), the 2010 Fannie Mae / Freddie Mac delistings, and First Republic Bank's failure (`FRCB`, 2023-05-03, ~$0.33).
  - **Known blind spot:** spin-offs where the parent kept its ticker (e.g. GE / GE HealthCare) are not caught. Planned: in the features step, scan for single-day moves above ~25% and check each against corporate actions and earnings dates.

### earning_calendar
- Columns: `time_of_day_code`, `estimate`, `reported_earning`, `market_cap`, `stock_id`, `symbol_at_date`
- `time_of_day_code`: `BMO` (before market open: the price reacts on the report date) or `AMC` (after market close: the price reacts the next trading day). Anything else would become `UNKNOWN` (none so far).
- No dates beyond 2026-11-03 (the requests ended there), so no scheduled future reports.
- **`market_cap` is point-in-time but understated by later splits.** It appears to be split-adjusted price × the share count at the time (AAPL Jan 2004: $156M stored vs ~$8.7B actual; 56 = 2 × 7 × 4, Apple's later splits). Recent values (no later splits) are correct. Correct it in the events step with

  `true market cap = market_cap × unadjusted_close / close` (prices on the report date).
- For universe selection or features, use the market cap from **before** an event (previous report or start of year), never the event's own value: for BMO reports it may already include the reaction.
- Converted to decimal (73+ raw files stored it as an integer).

### ivx
- Columns: `iv_<T>d_<call|put|mean>` for T = 7, 14, 21, 30, 60, 90, 120, 150, 180, 270, 360, 720, 1080; plus `exchange`, `symbol_at_date`
- **The raw `price` column is dropped:** it contains broken values (max $60 billion per share, mean $1.36M). Use `stock_prices` for prices.
- **6.0 cap:** every IV column had a maximum of exactly 6.0 (600%). 1,528 cells were at the cap and are set to NaN; the long tenors each lost exactly 38 values, so these look like 38 entirely broken rows.
- Missing after cleaning: ~15.0k rows (0.4%) for the 7/14/21-day tenors (already missing in the raw data); 38 rows for 30-day and longer tenors.
- Use: the implied-vol term structure; implied earnings moves for the whole S&P via the term-structure method (see `03_events`).

### chains (option chains, 49 stocks)
- Source: `stock-opts-by-param`. Request filter: DTE 0–400, moneyness ±50%. One raw file per trade date per side.
- Coverage: NVDA daily 2015-01-02 → 2026 earnings days (4.26M rows, plus 2010–14 earnings days); the other 48 names: the last close before and the first close after each earnings report since 2015 (since 2010 for names up to ~MCD in the list; the rest after the quota reset).
- Columns renamed: `c_date`→`date`, `call_put`→`cp`, `stocks_id`→`stock_id`, `price_strike`→`strike`, `openinterest`→`open_interest`, `calc_OTM`→`otm_pct`, `Bid`→`bid`, `Ask`→`ask`. `price` is dropped.
- **`mid` = (bid + ask) / 2, computed by us.** IVolatility's `price` equals the mid on 96% of rows, but is set to **0 whenever the bid is 0**, so it is not used.
- **`otm_pct`** = percentage moneyness, signed so that positive = out of the money for both calls and puts (e.g. strike 11, underlying 20.13: (11 − 20.13) / 20.13 = −45.4%, an in-the-money call).
- **`preiv` vs `iv`** (confirmed with IVolatility):
  - `preiv` = IV solved from that row's own option price; `-1` if it could not be calculated (no usable quote). ~20% of NVDA rows.
  - `iv` = `preiv` where available, otherwise **interpolated** across strikes and expiries; also `-1` on ~2% of rows.
  - Both `-1`s are set to NaN. Use `preiv` for trades and implied moves (an interpolated IV is not a tradeable price).
- **Bid = 0** on ~6% of rows (no buyers, mostly far out of the money): the backtest must never fill a sale at a zero bid.
- **Contract key: (`company`, `date`, `expiration_date`, `strike`, `cp`).**
  - `option_id` is **missing in files before ~2018-04** (2,447 files have no `option_id` at all, 60 have it partly). Kept as a nullable integer (`Int64`) but never used as a key: deduplicating on it would collapse each day of those files to one row.
  - `option_symbol` is not a reliable key either: the option root changed over time (NVDA options used the root `UVA` in 2010).
- Sanity checks (per ticker): 0 duplicate contracts, 0 bid < 0, 0 expiration < date, 0 cp not in {C, P}, 0 strike ≤ 0. **ask < bid: 1 row in TSLA** (a crossed quote; left in, never filled in the backtest).
- `price_open` / `price_high` / `price_low` are entirely null in 19 files (not used).
- **SPX is not cleaned yet.** It is ~40M of the 49.2M chain rows, too large for 16GB RAM in one go. Plan: clean year by year (add a `years` filter to `load_raw` and a save that replaces one ticker-year). Not needed for `03_events` (an index has no earnings).

## Raw datasets not cleaned yet

### hv: `/equities/eod/hv`
- 538 tickers: **current members and ETFs only (survivorship-biased)**. Columns `<T>d HV` for T = 10–180, plus `price`. Use only as a cross-check.

### ivs and ivs-by-delta
- `ivs`: NVDA, SPX, SPY; yearly chunks; columns `Call/Put`, `IV`, `delta`, `strike`, `out-of-the-money %`, `period`.
- `ivs-by-delta`: 7 tickers incl. AAPL, IWM, MSFT, NVDA, QQQ; **MSFT only 2004–2008**. Columns `delta`, `iv`, `moneyness`, `period`. The rest (~530 tickers) comes with the `skew` group after the quota reset.

## Schema notes

- Effectively **one schema per dataset**, except as noted. The extra schema variants are:
  - columns that are entirely null in a file (stored with type `null`)
  - `market_cap` stored as `int64` instead of `double` in some calendar files (all whole numbers)
  - chains: `option_id` missing or partly missing before ~2018-04; `price_open/high/low` null in 19 files
- Cleaning casts to one type per column.
- Company ID has two names: `stock_id` (calendars) and `stocks_id` (chains); both are `stock_id` after cleaning. `stock-prices` and `ivx` have no ID column.
- Raw column names are inconsistent (`Ask` vs `ask`, spaces, `%`). All clean columns are `snake_case`.

## Lookahead warnings

- `reported_earning` is only known **after** the announcement. Never use it (or any surprise built from it) as a feature for that same event. `estimate` is fine.
- IVolatility's earnings "actual move" fields are the target, not features.
- Event timing depends on `time_of_day_code` (BMO: same day; AMC: next day). Off by one day = measuring an ordinary day instead of the earnings jump.
- The calendar holds **actual** report dates, not the dates expected at the time. Fine for large caps (dates are confirmed weeks ahead); state it as a limitation.
- `market_cap` on a BMO report date may include that day's reaction.

## Known gaps and limitations

- **To download after the quota resets:** 2010–14 earnings chains for the rest of the 49 names (~1,496 jobs), and `ivs-by-delta` for ~530 tickers (~2,649 jobs).
- **SPX chains** downloaded (2004–2026) but not yet cleaned.
- **Symbols not found:** DALRQ, WNDXQ. Class shares (BRK.B, BF.B) were recovered as `BRK_B` / `BF_B`.
- **Survivorship bias:** `hv` covers current members only; earnings calendars were mostly empty for former members (partly recovered by the paid download's rename handling).
- **Selection bias:** the 49-name option-chain universe is *today's* large caps. Planned fix: a point-in-time universe (e.g. top 50 by corrected market cap each January) with the spare calls of a future quota cycle.
- **Old option data:** before ~2010 there were no weekly options and quotes were thinner (e.g. MCD 2010: ~61 contracts per side vs thousands for recent NVDA days), so implied moves are noisier. Check results on the post-2010 subsample.