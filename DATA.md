# DATA.md — data dictionary, cleaning rules and known gaps

Last updated: 2026-11-14. After every download, rerun `scripts/01_manifest.py` → `02_clean.py` → `03_events.py` and update this file.

## Sources

| Source | What | Where |
|---|---|---|
| IVolatility REST API (end-of-day) | prices, implied vol, historical vol, option chains, earnings calendars | `DATA_ROOT/ivol_data/` |
| Databento | NVDA minute-level options BBO, 2025 (plus ~$125 credit; planned: a small OPRA quote sample to check end-of-day bid/ask realism) | separate folder, not part of `ivol_data` |
| hanshof/sp500_constituents (GitHub) | daily S&P 500 membership history | `sp500_former_members.csv` (409 members that left since 2004) |
| Wikipedia | current S&P 500 members | `sp500_universe.csv` |

Downloaded with `scripts/00_download.py` (run from `DATA_ROOT`).
- **Plan:** IVolatility **Builder**, 20,000 end-of-day calls a month. **The quota resets on the 13th** (confirmed 2026-11-13: the account showed 20,000 left, then 19,996 after a 4-call test). Download scripts use `BILLING_DAY = 13` and `BUDGET = 19_000`.
- IVolatility counts exactly one request per data call. Polling `/data/info` and downloading `/data/download` files do not count.
- Free trial runs: 2026-11-04 and 2026-11-05 (6,462 calls; these counted against the first paid month).
- Paid run 1: 2026-11-11 → 2026-11-12, 13,000 calls, 12,995 new files, 21.8M rows, 0 failures. Stopped at the budget as planned.
- Paid run 2: 2026-11-13, 1,501 calls. `earn_ext`: 1,496 of 1,496 files (the 2010–14 earnings chains for the rest of the 49 names), 229,746 rows, 0 failures. Rows per file range from 47 to 440, with no pile-up at a round number, so nothing was truncated.
- **`skew` (`ivs-by-delta`) is not on the Builder plan** (403 "You don't have the required tariff"; Quant and Lab only). It has been removed from `PRIORITY`. See *Skew* below.
- About 18,400 calls are left this cycle (until 2026-12-13); check the account usage page for the exact figure. Planned use: point-in-time earnings chains (see *Selection bias*).

## Layout

```
DATA_ROOT/
├── ivol_data/equities_eod_<dataset>/<ticker>/<file>         raw downloads, never edited
└── ev_data/
    ├── manifest/
    │   ├── {files,schemas}.parquet                          scripts/01_manifest.py
    │   └── calendar_rerequest.csv                           old symbols of renamed companies (see calendar gaps)
    ├── clean/
    │   ├── stock_prices/year=YYYY/*.parquet                 scripts/02_clean.py
    │   ├── earning_calendar/year=YYYY/*.parquet
    │   ├── ivx/year=YYYY/*.parquet
    │   └── chains/ticker=XXX/year=YYYY/*.parquet            split by ticker AND year
    └── processed/
        └── events.parquet                                   scripts/03_events.py (one file, not partitioned)
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

### Reading and writing (`src/earning_vol/io.py`)
- `load_clean(name, columns=, tickers=, start=, end=)` reads a clean dataset. The filters are pushed down to parquet, so only the matching rows reach memory. It drops `year` and returns `ticker` as a plain string.
- `load_derived(name, columns=)` reads a processed table, `DERIVED/processed/<name>.parquet`.
- `save_clean` deletes before writing (the whole dataset, or for chains only the tickers being saved). `save_derived` overwrites its single file. Reruns never duplicate data.
- **Raw names vs clean names.** The manifest, `load_raw` and `available_tickers` use the API's dataset names (`stock-prices`, `stock-opts-by-param`, `history-earnings-calendar`, …). The clean and processed tables use snake_case names (`stock_prices`, `chains`, `earning_calendar`, `events`). Convert with `RAW_DATASETS` in `config.py` (keyed by clean name), and never type a raw name as a string: a typo returns an empty result instead of an error.

## Manifest (2026-11-14, after paid run 2)

| Dataset | Tickers | Parquet | Empty | Rows | First | Last |
|---|---|---|---|---|---|---|
| history-earnings-calendar | 931 | 679 | 252 | 48,044 | 2004-01-06 | 2026-11-03 |
| hv | 538 | 2,469 | 221 | 2,724,330 | 2004-01-02 | 2026-11-03 |
| ivs | 3 | 68 | 1 | 5,739,136 | 2004-01-02 | 2026-11-03 |
| ivs-by-delta | 7 | 84 | 1 | 6,311,182 | 2004-01-02 | 2026-11-03 |
| ivx | 964 | 4,202 | 489 | 3,552,737 | 2004-01-02 | 2026-11-03 |
| stock-opts-by-param | 50 | 23,870 | 204 | 49,412,040 | 2004-01-02 | 2026-11-03 |
| stock-prices | 964 | 3,320 | 417 | 3,646,597 | 2004-01-02 | 2026-11-03 |

Paid run 2 added exactly its 1,496 chain files and 229,746 rows (from 22,374 files / 49,182,294 rows); every other dataset is unchanged.

Flags: 0 zero-row files, 0 unreadable files, 0 bad dates, 0 `.tmp` files, 0 files with dates outside their name's range, 0 chain files containing the wrong day. Schema variants: 105 (calendars), 19 (hv), 3,782 (chains; up from 2,526 because most of the new 2010–14 files have no `option_id`), all handled in cleaning (see schema notes).

Paid run 1 added 25 tickers to prices, `ivx` and the calendars: recovered renames, bankrupt names under their OTC tickers, and the class shares (`BRK_B`, `BF_B`).

## Clean layer (2026-11-14)

| Clean dataset | Rows in | Rows out | Notes |
|---|---|---|---|
| `stock_prices` | 3,646,597 | 3,639,381 | 10 corporate-action days flagged (after adding FRCB to `REAL_MOVES`) |
| `earning_calendar` | 48,044 | 48,035 | 0 duplicates; 27,354 BMO, 20,681 AMC, 0 UNKNOWN |
| `ivx` | 3,552,737 | 3,549,501 | 0 duplicates; 1,528 capped IV cells set to NaN |
| `chains` | 9,636,100 | 9,636,100 | 49 stocks (+229,746 rows from paid run 2); 0 duplicate contracts; **SPX not cleaned yet** |

`events` (processed) is unchanged by paid run 2: 44,085 events, since the calendar did not change.

Checks after the run: readback counts match for all four; **no symbol appears under two folders on the same date** in prices, `ivx` or the calendar (the BBT recheck did not mix companies). The 2026-11-13 rerun, after moving `save_clean` into `io.py` and switching to `RAW_DATASETS`, reproduced every count exactly.

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
- **Ticker reuse:** `BBT` was BB&T until 2019 (its history is now in the `TFC` folder); the `BBT` folder holds a different bank (formerly `BHLB`) that took the ticker later. The calendar shows the same pattern for old S&P members whose tickers now belong to other companies, e.g. `WB` (Wachovia → Weibo), `PD` (Phelps Dodge → PagerDuty), `LU` (Lucent → Lufax), `G` (Gillette → Genpact), `BUD` (Anheuser-Busch → AB InBev), `EC` (Engelhard → Ecopetrol). These events drop out in `03_events` because there are no matching prices.
- **Restructurings:** `DD` (formerly DowDuPont / Dow) and `JCI` (pre-2016 history is Tyco's) change business at the switch. Treat these as structural breaks in vol modelling.
- **Bankrupt / delisted names** are stored under their OTC ticker (e.g. `SIVBQ`, `FRCB`), so `company` is that ticker.

### stock_prices
- Columns: `open`, `high`, `low`, `close`, `unadjusted_close`, `bid`, `ask`, `bid_size`, `ask_size`, `volume`, `exchange`, `symbol_at_date`, `corporate_action`
- Sanity checks (all 0): close ≤ 0, missing close, high < low, close outside [low, high], duplicate (company, date).
- **Split adjustment:** `open`/`high`/`low`/`close` are adjusted for all later splits; `unadjusted_close` is the actual traded price. Verified on NVDA 2021-07-13: `unadjusted_close / close = 40` (= 4 × 10, both splits), and `low ≤ close ≤ high`. The ratio being exactly 40 suggests prices are adjusted for **splits only, not dividends**.
  - **TODO:** confirm the overnight ratio `open_t / close_{t-1} ≈ 1` across 2021-07-20 and 2024-06-10.
- Realised vol uses the adjusted prices. Option moneyness and ATM strike selection use `unadjusted_close` (strikes are unadjusted).
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
  - None of the 10 flagged days is an earnings reaction day (0 events affected).

### earning_calendar
- Columns: `time_of_day_code`, `estimate`, `reported_earning`, `market_cap`, `stock_id`, `symbol_at_date`
- `time_of_day_code`: `BMO` (before market open: the price reacts on the report date) or `AMC` (after market close: the price reacts the next trading day). Anything else would become `UNKNOWN` (none so far).
- No dates beyond 2026-11-03 (the requests ended there), so no scheduled future reports.
- **For many renamed companies the history only starts at the rename** (e.g. META from 2022). See *Earnings calendar gaps*.
- **`market_cap` is point-in-time but understated by later splits.** It appears to be split-adjusted price × the share count at the time (AAPL Jan 2004: $156M stored vs ~$8.7B actual; 56 = 2 × 7 × 4, Apple's later splits). Recent values (no later splits) are correct. Correct it in the events step with

  `true market cap = market_cap × unadjusted_close / close` (prices on the report date).
- For universe selection or features, use the market cap from **before** an event (previous report or start of year), never the event's own value: for BMO reports it may already include the reaction.
- Converted to decimal (73+ raw files stored it as an integer).

### ivx
- Columns: `iv_<T>d_<call|put|mean>` for T = 7, 14, 21, 30, 60, 90, 120, 150, 180, 270, 360, 720, 1080; plus `exchange`, `symbol_at_date`
- **The raw `price` column is dropped:** it contains broken values (max $60 billion per share, mean $1.36M). Use `stock_prices` for prices.
- **6.0 cap:** every IV column had a maximum of exactly 6.0 (600%). 1,528 cells were at the cap and are set to NaN; the long tenors each lost exactly 38 values, so these look like 38 entirely broken rows.
- Missing after cleaning: ~15.0k rows (0.4%) for the 7/14/21-day tenors (already missing in the raw data); 38 rows for 30-day and longer tenors. **This matters for the term-structure implied move**, which leans on the short tenors: those events fall back to 30d or are skipped.
- Use: the implied-vol term structure; implied earnings moves for the whole S&P via the term-structure method.

### chains (option chains, 49 stocks)
- Source: `stock-opts-by-param`. Request filter: DTE 0–400, moneyness ±50%. One raw file per trade date per side.
- Coverage: NVDA daily 2015-01-02 → 2026 plus earnings days 2010–14 (4.26M rows). The other 48 names: the last close before and the first close after each earnings report **since 2010** (2010–14 completed by paid run 2). Days are chosen from the earnings calendar, so the renamed companies' missing calendar years (e.g. META before 2022) have **no chains** either.
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
- Sanity checks (per ticker): 0 duplicate contracts, 0 bid < 0, 0 expiration < date, 0 cp not in {C, P}, 0 strike ≤ 0. **ask < bid: 1 row each in TSLA and JPM** (crossed quotes; JPM's appeared with the 2010–14 files; left in, never filled in the backtest).
- `price_open` / `price_high` / `price_low` are entirely null in 19 files (not used).
- **SPX is not cleaned yet.** It is ~40M of the 49.2M chain rows, too large for 16GB RAM in one go. Plan: clean year by year (add a `years` filter to `load_raw` and a save that replaces one ticker-year). Not needed for `03_events` (an index has no earnings).

## Processed: events (`processed/events.parquet`, `scripts/03_events.py`)

One row per earnings event that has prices on both its entry and reaction day.

**Construction**
1. **Trading calendar** = the dates SPY traded, from `stock_prices`.
2. **Reaction day:** BMO → the first trading day on or after the report date; AMC → the first trading day *after* the report date (`searchsorted`, `side="left"` for BMO and `side="right"` for AMC). **Entry day** = the trading day before the reaction day. Weekend and holiday reports roll forward correctly (e.g. a Saturday report before Memorial Day reacts on the Tuesday).
3. **Prices** (split-adjusted, so the ratios are right across splits): `close_entry` on the entry day; `open_reaction`, `close_reaction` and `corporate_action` on the reaction day.
4. **Moves:** `r_event` = log(`close_reaction` / `close_entry`), `abs_move` = |`r_event`|, `gap` = log(`open_reaction` / `close_entry`) (the overnight part of the move).
5. **Labels:** `has_chains` = the company is one of the 49 chain names (**company-level**: whether a given event actually has a chain on its entry day is decided in the implied-move step); `is_holdout` = `report_date` ≥ `HOLDOUT_START` (2024-01-01).

Columns: `ticker`, `company`, `report_date`, `time_of_day_code`, `entry_date`, `reaction_date`, `close_entry`, `open_reaction`, `close_reaction`, `corporate_action`, `r_event`, `abs_move`, `gap`, `estimate`, `market_cap`, `stock_id`, `symbol_at_date`, `has_chains`, `is_holdout`. (`reported_earning` is dropped on load, see lookahead warnings.)

**Counts: 48,035 calendar events → 44,085 events.** Every lost event is accounted for:

| Reason | Events | Notes |
|---|---|---|
| Reaction day beyond the data | 22 | reports after 2026-11-03's last trading day |
| Company has no prices at all | 536 | 18 old members (AT, H, VRTS, MMI, WB, AM, PD, ADCT, ASO, CCU, DYN, EQ, GP, LU, TE, WFG, CR, LB); every price download came back `.empty`, so the source has nothing |
| Event before the company's first price | 668 | former members: prices were only downloaded around their membership (see survivorship bias) |
| Event after the company's last price | 2,724 | as above; also tickers reused by other companies after delisting |
| Missing price inside the price range | 1 | ROL, reaction day 2009-07-29 |
| **Total** | **3,951** | one event falls in two rows (beyond the data *and* missing a price), so the script's figure is 3,950 |

**Checks (2026-11-13), all passed**

| Check | Result |
|---|---|
| NVDA 2023-05-24 (AMC) | entry 05-24, reaction 05-25, move +24.4% (`r_event` 0.218) |
| NFLX 2022-04-19 (AMC) | entry 04-19, reaction 04-20, move −35.1% (`r_event` −0.433) |
| META 2022-02-02 | not in the calendar (rename gap, see below) |
| Median `abs_move` | 3.0% (mean `r_event` +0.11%, mean `gap` +0.07%) |
| Companies with `has_chains` | 49 (4,233 events) |
| `is_holdout` | 6,110 events (13.9%); 37,975 before 2024 |
| Events on corporate-action days | 0 |

Timing test, the median |daily log return| around the reaction day. If the timing were off by a day, the spike would sit on day −1 or +1.

| Day | −3 | −2 | −1 | **0** | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|
| Median \|return\| | 0.0096 | 0.0097 | 0.0106 | **0.0300** | 0.0131 | 0.0108 | 0.0102 |

Day 0 is 2.5× the average of days ±1 and about 3× the quiet days. Day +1 is slightly raised, which is normal (vol stays high after earnings).

## Earnings calendar gaps (renamed companies)

For many renamed companies, the earnings calendar **starts at the rename**, while prices (tracked by `stock_id`) go back further. Found by comparing each company's first calendar event with its first price date (`notebooks/check_calendar_gaps.py`).

- **90 companies with old symbols** in `symbol_at_date`, about 3,200 events missing (upper bound: assumes events back to the first price). Examples: META (FB, from 2022), BKNG (PCLN, from 2018), RTX (UTX, from 2020), ELV (ANTM/WLP, from 2022), LUMN (CTL, from 2020), GOOGL (GOOG, from 2010). The list of old symbols is in `manifest/calendar_rerequest.csv`.
- **16 companies with a late start and no old symbol**, about 470 events: mergers, bankruptcies and new listings where the calendar restarted (e.g. FTI 2017 merger, DAL and CHTR bankruptcies, CRH's US listing). Not fixable from this source.

**Cause, confirmed on 2026-11-13 (about 25 calls):**
- Requesting the old symbol returns 0 rows with no notice (FB, ANTM, ATH, WLP tested).
- Requesting by `stockID` returns the same truncated history. FB and META share `stock_id` 22712, but the security record was re-created at the rename (US start date now 2022-06-09), and the earnings archive restarts there. A NASDAQ-100 scan of 2012–2016 (1,450 events) contains no FB row at all.
- It varies by security: SQ → XYZ kept its full history back to 2016; META, ELV and LUMN did not.

**Consequences and handling**
- The sample is about 7% smaller. The kill test is unaffected: among the 49 chain names only META, GOOGL, MS and T lose early events, and those events have no chains anyway.
- **Benchmark B (historical-average move) requires at least 8 prior events**, otherwise NaN, so that a history which restarts at a rename is not passed off as a full one.
- **Fix, for later:** SEC EDGAR 8-K Item 2.02 filings ("Results of Operations"), keyed by CIK, which survives renames. The filing timestamp also gives BMO/AMC. It doubles as a robustness check on IVolatility's dates and timing codes for the overlapping events.

## Skew

- `ivs-by-delta` (ready-made IV by delta) is Quant/Lab only. Not needed:
  - **Entry-day skew** comes from the chains (49 names, plus any names added later).
  - **Daily skew series** can come from `ivs` (full surface with a `delta` column), but `ivs` currently covers only NVDA, SPX and SPY.
- Definitions (30-day tenor): RR25 = σ(25Δ call) − σ(25Δ put) (usually negative, puts are richer); put skew = σ(25Δ put) − σ(50Δ). On a call-delta axis, a 25Δ put sits at 0.75.
- Cost of more `ivs`: the existing files are **yearly chunks**, so about 23 calls per symbol for 2004–2026 (49 names ≈ 1,100 calls; all ~660 ≈ 15,000). Rows are free, so first test whether one call can cover several years.

## Raw datasets not cleaned yet

### hv: `/equities/eod/hv`
- 538 tickers: **current members and ETFs only (survivorship-biased)**. Columns `<T>d HV` for T = 10–180, plus `price`. Use only as a cross-check.

### ivs and ivs-by-delta
- `ivs`: **NVDA, SPX and SPY only**; yearly chunks; columns `Call/Put`, `IV`, `delta`, `strike`, `out-of-the-money %`, `period`.
- `ivs-by-delta`: 7 tickers incl. AAPL, IWM, MSFT, NVDA, QQQ (downloaded during the free trial); **MSFT only 2004–2008**. Columns `delta`, `iv`, `moneyness`, `period`. **No more can be downloaded on Builder.**

## Other IVolatility endpoints worth knowing

- `/equities/eod/earnings`: **upcoming** earnings only (it ignores the date range), with IVolatility's own `implied_move`, stock price and straddle contracts. No history, so useless for the backtest, but a ready-made input and cross-check for **live trading**.
- `/equities/underlying-info?symbol=X&date=D`: what a ticker meant on a date (`StockID`, company, start/end dates). Useful for checking ticker reuse.

## Schema notes

- Effectively **one schema per dataset**, except as noted. The extra schema variants are:
  - columns that are entirely null in a file (stored with type `null`)
  - `market_cap` stored as `int64` instead of `double` in some calendar files (all whole numbers)
  - chains: `option_id` missing or partly missing before ~2018-04; `price_open/high/low` null in 19 files
- Cleaning casts to one type per column.
- Company ID has two names: `stock_id` (calendars) and `stocks_id` (chains); both are `stock_id` after cleaning. `stock-prices` and `ivx` have no ID column.
- Raw column names are inconsistent (`Ask` vs `ask`, spaces, `%`). All clean columns are `snake_case`.

## Lookahead warnings

- `reported_earning` is only known **after** the announcement. Never use it (or any surprise built from it) as a feature for that same event. `estimate` is fine. It is dropped when `03_events` loads the calendar.
- IVolatility's earnings "actual move" fields are the target, not features.
- Event timing depends on `time_of_day_code` (BMO: same day; AMC: next day). Off by one day = measuring an ordinary day instead of the earnings jump. Verified by the timing test above.
- The calendar holds **actual** report dates, not the dates expected at the time. Fine for large caps (dates are confirmed weeks ahead); state it as a limitation.
- `market_cap` on a BMO report date may include that day's reaction.
- Historical-average move features use **past events only** (strictly before the current report date).

## Known gaps and limitations

- **SPX chains** downloaded (2004–2026) but not yet cleaned.
- **Symbols not found:** DALRQ, WNDXQ. Class shares (BRK.B, BF.B) were recovered as `BRK_B` / `BF_B`.
- **Survivorship bias:**
  - `hv` covers current members only.
  - Former members' prices and `ivx` were only downloaded for the 5-year chunks overlapping **one year before joining to one year after leaving**, while their calendars cover 2004–2026. Former members are therefore trimmed to roughly their membership window, but **current members keep their full history, including years before they joined**. Planned fix: an explicit "in the index on this date" flag for every event, built from the membership dates, instead of relying on price coverage by accident.
- **Selection bias:** the 49-name option-chain universe is *today's* large caps, i.e. past winners, which biases straddle P&L (winners got there partly through big earnings surprises). Planned fix: include an event if the company was in the **top ~150 by split-corrected market cap on that date**, and spend the remaining calls of this cycle (before 2026-12-13) on those events' chains, 2015+ first (weekly expiries give cleaner implied moves). This also gives the kill test more holdout events, about 540 at present.
- **Calendar rename gaps:** about 3,700 events in total (see *Earnings calendar gaps*).
- **Old option data:** before ~2010 there were no weekly options and quotes were thinner (e.g. MCD 2010: ~61 contracts per side vs thousands for recent NVDA days), so implied moves are noisier. Check results on the post-2010 subsample.
- **Skew:** daily skew series exist only for NVDA, SPX and SPY (see *Skew*).

## Open TODOs

- Split check: overnight ratio `open_t / close_{t-1}` across NVDA's 2021-07-20 and 2024-06-10 splits.
- Make the manifest incremental (reuse results for files whose path, size and modified time are unchanged) and print progress.
- SPX chains: year-by-year cleaning.
- "In the index on this date" flag for events.
- Point-in-time chain download (top ~150 by corrected market cap).
- EDGAR 8-K calendar, for the rename gaps and as a timing robustness check.
- `ivs` for more names (test a multi-year range per call first).
