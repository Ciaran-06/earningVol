# Date:15/11/26

## Hypothesis
Realised/Implied is predictable from entry-day information and tradable after bid/ask

- H1: Forecasting
- H2: trading (bid/ask)

## Kill Test
- Pre 2024 data only: **ok** events (2665)
- Naive Rules: always sell; sell if implied > historical-average move; buy if below.
- Priced at bid on entry and ask on the reaction day (reverse for buys)

## Kill Criterion
- trading is killed if no rule has a positive mean P&L after costs with t > 2 and a linear model's out of sample R^2 <= 0. If killed, the project continues as a forecasting-only paper

## Current Decesion
### Data
- Rename gaps in the calendar are accepted for now (EDGAR is later fix)
- No upgrade for skew. Entry-day skew comes from the chains, and the daily skew from ivs
- Prices for options use unadjusted close and the chain's underlying price. Strikes are real historical strkes, so they must be compared with the real traded price.
- Market cap is corrected by the entry-day split factor and carried forward for missing values. That remove the split understatement, and a cap quarter old is close enough for ranking.
- BRK_B's treatment in the universe still to be decided. It has no cap but is always among the lagest companies.
### Events
- Entry is t he close before the news, and the reaction day is the first close after it (BMO/AMC rule). This was verifed by the timeing test.
- **Straddle Rules**
    - expirey: the earliest on or after the reaction day, so the options covers the move.
    - strike: the ATM strike where both legs have a real quote, so the price is tradable.
    - exit: the saame contracts at whatever the quote exists, becuase that's the price you'd actually face.
- Moves are measured as simple returns, not log returns, becuase a straddle pays a simple move
- Benchmark B uses the previous 8 events and needs all 8, which avoids lookahead and stops short histories posing as full ones.
- Zero moves are floored at 0.1%, not dropped. Dropping them would bias the sample against selling
### Research Design
- The holdout is 2024 onwards and stays untouched until the end, so the final result is honest.
- The Kill Criterion uses naive rules at bid/ask on pre 2024 data, with its criterion written in advance. That prevents choosing the rule after seeing results.
- Features wait until after the kill criterion result. The outcome decided what the features are for. 