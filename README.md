# earningVol

**Is the earnings move predictable relative to what options price in, and can you trade it after costs?**

An event study of 44,085 S&P 500 earnings announcements (2004–2026), with at-the-money straddles priced from end-of-day option chains for 49 large-cap names (2010–2026). The trading question was tested with a kill criterion written and committed to git before any P&L was computed.

**Result: no.** All three simple straddle rules lose money after bid/ask costs (mean −5.5% to −7.2% of the premium per trade, $t$ between −2.8 and −5.5). A one-feature linear model beats its benchmark out of sample, but only just ($R^2 = 0.0026$). The signal points the right way; the bid/ask spread is several times larger than the edge.

---

## The question

For each earnings event, compare the move that happened with the move the options priced in:

$$y = \log\left(\frac{m}{M^{\text{imp}}}\right), \qquad m = \left|\frac{C_{\text{reaction}}}{C_{\text{entry}}} - 1\right|, \qquad M^{\text{imp}} = \frac{\text{ATM straddle mid}}{S}$$

- $y < 0$: the stock moved less than priced (good for a seller)
- $y > 0$: it moved more (good for a buyer)

Two hypotheses:
- **H1 (forecasting):** entry-day information predicts $y$ out of sample.
- **H2 (trading):** a simple rule built on it makes money on ATM straddles after bid/ask costs.

## Result

Kill test on pre-2024 events (n = 2,620; the 2024+ holdout was not touched). P&L is per trade, as a fraction of the entry premium, selling at the bid and buying at the ask.

| Rule | n | Mean P&L | t |
|---|---|---|---|
| Always sell the straddle | 2,620 | −6.7% | −5.51 |
| Sell if implied move > average of last 8 moves | 1,914 | −5.5% | −4.14 |
| Buy if implied move < average of last 8 moves | 706 | −7.2% | −2.79 |

| Linear model ($y$ on $\log(B/M^{\text{imp}})$) | Value |
|---|---|
| Train / test | 2010–18 (1,663) / 2019–23 (957) |
| Slope $b$ | 0.41 |
| Out-of-sample $R^2$ vs training mean | **0.0026** |

**Verdict (pre-registered):** H1 pass, H2 fail, so trading is killed as specified.

**Robustness (pre-registered):** from 2013 onwards, once weekly options make the implied move almost purely an earnings move, every rule still loses, and selling gets *worse* (always sell −7.7%, $t = -5.4$).

**Why "options are overpriced" doesn't pay:** the median realised/implied ratio is 0.70, but a seller earns the *mean* of roughly $1 - \text{ratio}$, and a few huge moves dominate it. NVDA on 2023-05-24: options priced a 7.2% move, the stock moved 24.4%, and a straddle seller lost 248% of the premium overnight.

Full numbers, caveats and follow-ups: [NOTES.md](NOTES.md).

## Documentation

| File | What it holds |
|---|---|
| [METHODS.md](METHODS.md) | Every construction step (sample, event timing, moves, straddles, target, market cap) with its reason and a check |
| [DATA.md](DATA.md) | Data dictionary, cleaning rules, every count in and out, known gaps and biases |
| [NOTES.md](NOTES.md) | Hypotheses, the pre-registered kill test, the result, and dated decisions |

## Pipeline

```
scripts/
  00_download.py    raw end-of-day data from the IVolatility API
  01_manifest.py    inventory and integrity checks of every raw file
  02_clean.py       clean layer: prices, earnings calendar, IVX, option chains
  03_events.py      one row per earnings event: timing, moves, benchmark, straddles, target
  04_kill_test.py   the pre-registered kill test and robustness table

src/earning_vol/
  config.py         paths, dates (holdout from 2024-01-01), dataset names
  io.py             load_clean / save_clean / load_derived / save_derived
  manifest.py       raw-file inventory
  clean.py          cleaning rules
  events.py         event construction and ATM straddle pricing
  strategy.py       kill-test sample, straddle P&L, rules, summary, linear model

notebooks/          check scripts (.py): known-answer tests, regression checks, data-quality checks
```

### Running it

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Set the data paths in `src/earning_vol/config.py`, then:

```
uv sync
uv run python scripts/01_manifest.py
uv run python scripts/02_clean.py
uv run python scripts/03_events.py
uv run python scripts/04_kill_test.py
```

**No data is included.** The raw data comes from a paid IVolatility subscription and cannot be redistributed.

## How the work was checked

- **Known answers:** NVDA 2023-05-24 is traced end to end (timing, move, straddle, target, P&L) and matched to hand calculations.
- **Timing test:** the median absolute return spikes on the reaction day (0.030, against about 0.010 on surrounding days), so the BMO/AMC timing is right.
- **Counts in and out:** every dropped event is explained (48,035 calendar events → 44,085).
- **Unit and regression tests:** hand-built straddle-picking cases, and reruns compared with the previous output (0 changed strikes after the tie-rule fix).
- **Pre-registration:** the kill criterion, sample, pricing and robustness check were committed (`985103f`) before the first P&L was computed.

## Limitations

- **Selection bias:** the 49 option-chain names are today's large caps (past winners). This biases against selling, but is unlikely to flip the result.
- **Not point-in-time:** current S&P members keep years of history from before they joined the index.
- **End-of-day quotes:** closing bid/ask spreads may be wider than what could be traded intraday.
- **Calendar gaps:** for some renamed companies the earnings history starts at the rename (about 7% of events missing).
- **Weak H1 pass:** the out-of-sample $R^2$ was not tested for significance.

## Status

Closed at the kill test (November 2026). Possible follow-ups (cost diagnostics, holding to expiry, a point-in-time universe) are listed in NOTES.md.