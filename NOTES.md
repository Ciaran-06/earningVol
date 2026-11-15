# Notes - Last Updated 15/11/26

## Hypothesis
The ratio of realised to implied move is predictable from entry-day information, and the prediction is tradable after bid/ask costs.

- **H1 (forecasting):** entry-day information predicts $y = \log(m / M^{\text{imp}})$ out of sample.
- **H2 (trading):** a simple rule built on that information makes money on ATM straddles after bid/ask costs.

## Kill Test (fixed before seeing results)

### Sample
- Pre-2024 `ok` events (2,665) **that also have `hist_move_8`**. Every rule and the linear model use this same sample; the final count is logged with the result.
- *Reason:* rules 2 and 3 need benchmark B, so running "always sell" on a larger sample would make the comparison unfair.

### Rules
1. Always sell the straddle.
2. Sell if the implied move is above benchmark B ($M^{\text{imp}} > B$).
3. Buy if the implied move is below benchmark B ($M^{\text{imp}} < B$).

### Pricing and P&L
- One straddle per event, opened at the entry-day close and closed at the reaction-day close (not held to expiry).
- Sell: sell at the entry bid, buy back at the exit ask. Buy: buy at the entry ask, sell at the exit bid.
- P&L is measured as a fraction of the entry premium:
$$\text{P\&L}_{\text{sell}} = \frac{\text{entry bid} - \text{exit ask}}{\text{entry mid}}, \qquad \text{P\&L}_{\text{buy}} = \frac{\text{exit bid} - \text{entry ask}}{\text{entry mid}}$$
- *Reason:* dividing by the premium makes a \$20 stock and a \$900 stock comparable, and it is on the same scale as the move ratio.
- The t-statistic is $\bar{x} / (s / \sqrt{n})$ over events.

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