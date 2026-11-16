# Notes - Last Updated 16/11/26

## Hypothesis
The ratio of realised to implied move is predictable from entry-day information, and the prediction is tradable after bid/ask costs.

- **H1 (forecasting):** entry-day information predicts $y = \log(m / M^{\text{imp}})$ out of sample.
- **H2 (trading):** a simple rule built on that information makes money on ATM straddles after bid/ask costs.

## Kill Test (fixed before seeing results)

### Sample
- Pre-2024 (`is_holdout` False) `ok` events **that also have `hist_move_8`**. Every rule and the linear model use this same sample.
- **n = 2,620** (44,085 events → 37,975 pre-2024 → 2,665 `ok` → 2,620 with `hist_move_8`), report dates 2010-01-14 to 2023-12-21. Fixed 2026-11-16 by `strategy.kill_sample`, before any P&L was computed.
- *Reason:* rules 2 and 3 need benchmark B, so running "always sell" on a larger sample would make the comparison unfair.

### Rules
1. Always sell the straddle.
2. Sell if the implied move is above benchmark B ($M^{\text{imp}} > B$).
3. Buy if the implied move is below benchmark B ($M^{\text{imp}} < B$).
- An event with $M^{\text{imp}} = B$ exactly is traded by neither rule 2 nor rule 3.

### Pricing and P&L
- One straddle per event, opened at the entry-day close and closed at the reaction-day close (not held to expiry).
- Sell: sell at the entry bid, buy back at the exit ask, floored at intrinsic value. Buy: buy at the entry ask, sell at the exit bid.
- P&L is measured as a fraction of the entry premium:
$$\text{P\&L}_{\text{sell}} = \frac{\text{entry bid} - \max\left(\text{exit ask},\ |S_{\text{exit}} - K|\right)}{\text{entry mid}}, \qquad \text{P\&L}_{\text{buy}} = \frac{\text{exit bid} - \text{entry ask}}{\text{entry mid}}$$
- *Reason:* dividing by the premium makes a \$20 stock and a \$900 stock comparable, and it is on the same scale as the move ratio.
- **Intrinsic floor:** a seller's buy-back is priced at $\max(\text{exit ask},\ |S_{\text{exit}} - K|)$.
    - *Reason:* a straddle can't be bought below its intrinsic value, so an ask below it is a timing artefact or a bad quote. The floor only ever makes selling look worse, so it is conservative.
    - *Evidence:* 10 events affected by a few cents (max \$0.40); negligible now, but it protects later universes.
- **Mean and t-statistic per traded event:** each rule's mean and $t = \bar{x} / (s / \sqrt{n})$ are taken over the events that rule trades only. Untraded events are not counted as 0.
    - *Reason:* counting untraded events as 0 changes both the mean and the t-statistic, so the choice is fixed before any P&L is seen.
- *Check:* NVDA 2023-05-24: sell $= (21.25 - 75.37)/21.83 = -2.480$, buy $= (73.96 - 22.40)/21.83 = 2.362$, matching `strategy.straddle_pnl`.

### Linear model
- OLS of $y$ on a single feature, $x = \log(B / M^{\text{imp}})$.
- Train: `report_date` 2010–2018. Test: 2019–2023.
- Out-of-sample $R^2 = 1 - \text{SSE}_{\text{model}} / \text{SSE}_{\text{bench}}$, where the benchmark predicts the **training-set mean of $y$** for every test event. The benchmark $\hat y = 0$ ("the implied move is right on average") is reported alongside it.
- *Reason:* the training mean is the tougher benchmark, because it already captures the average variance risk premium. A positive $R^2$ against it means the feature adds information beyond "options are usually overpriced".

## Kill Criterion
- **H1 passes** if the linear model's out-of-sample $R^2 > 0$ against the training-mean benchmark.
- **H2 passes** if at least one rule has a positive mean P&L after costs with $t > 2$.

| H1 | H2 | Decision |
|---|---|---|
| pass | pass | Continue the full project: features, models, then the holdout. |
| pass | fail | Trading is killed. Continue as a forecasting-only paper. |
| fail | pass | Treat it as a premium, not a prediction: check whether only "always sell" passes. If so, that is the known variance risk premium, and the project's question has failed. Reassess before building features. |
| fail | fail | Stop and write up the negative result. Reassess the question before spending more data calls. |

### Caveats (stated in advance)
- Many reports fall in the same weeks, so events are not independent and $t > 2$ overstates confidence. A robustness check clustered by reaction week comes later.
- Three rules are tested, so the best of three passing $t > 2$ is easier than one pre-chosen rule passing. Report all three, not just the best.

### Robustness (reported, not part of the criterion)
- **Post-weeklies sample:** the same three rules, rerun on pre-2024 `ok` events with a report date on or after 2013-01-01.
- *Reason:* before weekly options, the chosen expiry often ran well past the reaction day (median 23 days in 2010, 4 in 2011). Those implied moves include non-earnings time value, which inflates them and biases the test toward selling. From 2013, over 93% of events expire within a week of the reaction day.
- *How it's read:* reported next to the main result. If "always sell" passes on the full sample but not from 2013, the full-sample pass is most likely the expiry artefact, not an edge.
- Chosen on 2026-11-16 from the days-to-expiry table (DATA.md), before any P&L was computed.

## Kill Test Result (2026-11-16)

Pre-registration commit: `985103f` (made before the run). Code: `src/earning_vol/strategy.py`.

### Rules (n = 2,620, P&L as a fraction of the entry premium, after bid/ask)

| Rule | n | Mean P&L | Std | t |
|---|---|---|---|---|
| Always sell | 2,620 | −6.7% | 0.620 | −5.51 |
| Sell rich ($M^{\text{imp}} > B$) | 1,914 | −5.5% | 0.584 | −4.14 |
| Buy cheap ($M^{\text{imp}} < B$) | 706 | −7.2% | 0.684 | −2.79 |

No ties: sell rich + buy cheap = 2,620.

### Linear model (train 2010–18, test 2019–23)

| n train | n test | $a$ | $b$ | $R^2$ vs training mean | $R^2$ vs 0 |
|---|---|---|---|---|---|
| 1,663 | 957 | −0.511 | 0.406 | **0.0026** | 0.229 |

Checks: scoring the training mean as the model gives $R^2 = 0.0$ against itself; 1,663 + 957 = 2,620.

### Verdict
- **H1: pass** ($R^2 = 0.0026 > 0$), but only just. The gain is 0.26% of squared error and was not tested for significance.
- **H2: fail.** No rule has a positive mean; all three are significantly negative.
- **Decision (from the table above): trading is killed as specified. The project continues as a forecasting-only paper.**

### Reading the result (interpretation, not new tests)
- **$b = 0.41$:** past moves carry some information that options do not fully price. At $x = 0$, the predicted ratio is $e^{-0.51} \approx 0.60$ (the variance risk premium).
- **The failure is cost, not direction.** For the same event, $\text{P\&L}_{\text{sell}} + \text{P\&L}_{\text{buy}} = -(\text{entry spread} + \text{exit spread})/\text{entry mid}$. Backing out from the totals:
    - selling the 706 cheap events made $-0.098$, so their two spreads total about 17% of the premium (about 8.5% per round trip)
    - buy cheap at mid $\approx (-0.072 + 0.098)/2 = +1.3\%$
    - sell rich at mid $\approx +3\%$, *if* rich events have similar spreads (an assumption)
    - so the signal points the right way in both directions, but the cost is several times the edge
    - these are back-of-envelope estimates found after seeing the results; they are not evidence. **The exact numbers are in Follow-ups → Cost diagnostics** (buy cheap at mid: +1.3%, as estimated; sell rich at mid: +3.9%, slightly above the estimate)
- **The median ratio of 0.70 is not what a seller earns.** A seller earns roughly the *mean* of $1 - \text{ratio}$, and a few very large ratios (e.g. NVDA 2023-05-24, −248%) pull that mean down.

### Caveats on the result
- **Selection bias:** the 49 names are today's large caps, which got there partly through big earnings moves. That biases against selling. It is unlikely to flip a mean of −6.7% with $t = -5.5$.
- **End-of-day quotes:** closing bid/ask may be wider than what could be traded intraday, so the costs may be overstated. Not tested.
- **Independence:** clustered event dates make the t-statistics overstate confidence (in both directions).

### Robustness: from 2013-01-01 (pre-registered above)

n = 2,098 (earliest report date 2013-01-11), same rules and pricing.

| Rule | n | Mean P&L | Std | t |
|---|---|---|---|---|
| Always sell | 2,098 | −7.7% | 0.652 | −5.44 |
| Sell rich ($M^{\text{imp}} > B$) | 1,517 | −6.2% | 0.618 | −3.93 |
| Buy cheap ($M^{\text{imp}} < B$) | 581 | −6.7% | 0.707 | −2.28 |

- **The result is robust:** every rule still loses, with $t$ well below −2. Dropping 2010–12 does not change the verdict.
- **Selling gets worse from 2013** (always sell −7.7% vs −6.7%; sell rich −6.2% vs −5.5%). That is the expected direction: before weekly options, the longer expiries inflated the implied move and flattered sellers.
- **Buy cheap is slightly less bad** (−6.7% vs −7.2%), but still significantly negative.

## Follow-ups (written before running any of them)

These are new questions raised by the result, so they are **not** part of the kill test and cannot change its verdict. At most two are run now; each is written here before it is run, and the holdout stays untouched.

### 1. Cost diagnostics (descriptive, no pass/fail)
- For each of the three rules: mean P&L at **mid** (entry mid to exit mid) and the mean **entry and exit spread** as a fraction of the entry mid.
- *Reason:* it replaces the back-of-envelope estimates above with exact numbers, and separates "no premium" from "costs eat the premium".

**Result (2026-11-16).** Code: `strategy.mid_pnl`, `strategy.spreads`, `strategy.cost_table`. Means per traded event; spreads and cost as a fraction of the entry mid; the exit ask is floored at intrinsic, as in the kill test.

Full sample (n = 2,620):

| Rule | n | P&L at bid/ask | t | P&L at mid | t | Cost per trade | Entry spread | Exit spread |
|---|---|---|---|---|---|---|---|---|
| Always sell | 2,620 | −6.7% | −5.51 | +2.5% | 2.13 | 9.2% | 8.8% | 9.6% |
| Sell rich | 1,914 | −5.5% | −4.14 | **+3.9%** | **3.02** | 9.4% | 9.1% | 9.8% |
| Buy cheap | 706 | −7.2% | −2.79 | +1.3% | 0.50 | 8.5% | 8.0% | 9.0% |

From 2013-01-01 (n = 2,098):

| Rule | n | P&L at bid/ask | t | P&L at mid | t | Cost per trade | Entry spread | Exit spread |
|---|---|---|---|---|---|---|---|---|
| Always sell | 2,098 | −7.7% | −5.44 | +2.5% | 1.84 | 10.3% | 9.7% | 10.9% |
| Sell rich | 1,517 | −6.2% | −3.93 | **+4.5%** | **2.92** | 10.7% | 10.2% | 11.2% |
| Buy cheap | 581 | −6.7% | −2.28 | +2.5% | 0.83 | 9.2% | 8.5% | 9.9% |

Checks: sell + buy + entry spread + exit spread = 0 on every event (max error 5e-16); mid sell + mid buy = 0 exactly; NVDA 2023-05-24 mid sell −2.421, entry spread 0.053, exit spread 0.065, matching hand calculations.

**Reading it (descriptive; it cannot change the kill-test verdict):**
- **There is an edge before costs, and it is in selling rich straddles.** At mid, sell rich makes +3.9% per trade ($t = 3.0$), and +4.5% from 2013. Always sell makes +2.5% (the variance risk premium, $t \approx 2$). Buy cheap is not distinguishable from zero.
- **The benchmark-B signal adds to the premium:** sell rich beats always sell at mid by about 1.4 points (2 points from 2013), consistent with $b = 0.41$.
- **Costs are 2–4 times the edge.** Crossing both spreads costs about 9–11% of the premium per trade, against a best edge of about 4%.
- **The cost is split roughly evenly between entry and exit** (each about 9–11% of the premium as a full spread; cost per trade ≈ half of each). Mean spreads are higher than the 6.6% median entry spread in DATA.md, so a minority of events have very wide spreads.
- **Spreads are wider from 2013.** Short-dated weekly straddles have small premiums, so the same spread in dollars is a larger fraction of the premium.
- **What this means for H3 (hold to expiry):** settling at intrinsic removes only the exit half (about 4.9% for sell rich). The seller still pays half the entry spread (about 4.5%), against an edge at mid of 3.9%, so H3 looks close to break-even at best. The residual time value at exit (which a seller would keep) could tip it either way.
- These are mid prices, which nobody trades at. A positive $t$ at mid is a description of the edge, not a tradable result.

### 2. H3: hold to expiry (new hypothesis)
- **Question:** does settling at expiry, instead of buying back on the reaction day, make any rule profitable after costs?
- **Rule:** the same sample (n = 2,620) and the same three rules. Entry as before (sell at the bid, buy at the ask). Instead of trading out on the reaction day, the straddle is **settled at intrinsic value** $|S_T - K|$, where $S_T$ is the unadjusted close on the expiry date (from `stock_prices`).
$$\text{P\&L}_{\text{sell}} = \frac{\text{entry bid} - |S_T - K|}{\text{entry mid}}, \qquad \text{P\&L}_{\text{buy}} = \frac{|S_T - K| - \text{entry ask}}{\text{entry mid}}$$
- **Criterion:** H3 passes if at least one rule has a positive mean P&L with $t > 2$.
- **Also reported:** events with `days_to_expiry = 0` (settlement on the reaction day itself, no extra days of risk), and events from 2013-01-01.
- *Reason:* settlement removes the exit spread, roughly half the round-trip cost. It also matches what the premium pays for: the move through expiry.
- *Caveats, stated in advance:*
    - for `days_to_expiry > 0`, the position carries ordinary-day risk until expiry
    - this is a second test on the same sample after seeing the first result, so a pass is weaker evidence than the kill test would have been, and needs the holdout to confirm it

### Parked (not run now)
- **Fraction of the spread paid:** report P&L as a function of the fraction of the spread paid. Its realistic value is chosen from the Databento NVDA quote sample **before** looking at the P&L.
- **Deciles of $x$:** gross P&L by decile of the feature, to see whether only the extremes clear the cost. Belongs to the forecasting paper.
- **Target design for later models:** for trading, the mean of the ratio (or P&L directly) matters, and the log target compresses the tail that decides it. Revisit when designing the transformer.
- **Pre-announcement straddles** (Gao, Xing & Zhang 2018, JFQA): buy about 3 days before the announcement and exit at the announcement date. It's a different trade (a bet on implied vol rising, not on the move), strongest in small, costly names. A separate project idea.
- **Significance of the H1 $R^2$:** a bootstrap over test events. If run, it is reported whatever it shows.

## Current Decisions

### Data
- Rename gaps in the calendar are accepted for now (EDGAR is the later fix).
- No upgrade for skew. Entry-day skew comes from the chains, and the daily skew from `ivs`.
- Option prices use the unadjusted close and the chain's underlying price. Strikes are real historical strikes, so they must be compared with the real traded price.
- Market cap is corrected by the entry-day split factor and carried forward for missing values. That removes the split understatement, and a cap a quarter old is close enough for ranking.
- BRK_B's treatment in the universe is still to be decided. It has no cap but is always among the largest companies.

### Events
- Entry is the close before the news, and the reaction day is the first close after it (BMO/AMC rule). This was verified by the timing test.
- **Straddle rules**
    - Expiry: the earliest on or after the reaction day, so the option covers the move.
    - Strike: the ATM strike where both legs have a real quote, so the price is tradable.
    - Exit: the same contracts at whatever quote exists, because that's the price you'd actually face.
- Moves are measured as simple returns, not log returns, because a straddle pays a simple move.
- Benchmark B uses the previous 8 events (about two years of quarterly reports) and needs all 8, which avoids lookahead and stops short histories posing as full ones.
- Zero moves are floored at 0.1%, not dropped. Dropping them would bias the sample against selling.

### Research Design
- The holdout is 2024 onwards and stays untouched until the end, so the final result is honest.
- The kill test uses naive rules at bid/ask on pre-2024 data, with its criterion written in advance. That prevents choosing the rule after seeing results.
- The kill test has its own fixed split (train 2010–18, test 2019–23), so the test period has enough events. The 2021-01-01 validation start in `config.py` applies to later model tuning (features, transformer), not to the kill test.
- Features wait until after the kill test result. The outcome decides what the features are for.
- **2026-11-16:** the kill test returned H1 pass, H2 fail. The project continues as a forecasting-only paper; trading questions continue only as pre-registered follow-ups (see above).