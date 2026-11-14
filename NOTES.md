## Hypothesis
Realised/Implied is predictable from entry-day information and tradable after bid/ask

- H1: Forecasting
- H2: trading

## Kill Test
- Pre 2024 data only.
- Naive Rules: always sell; sell if implied > historical-average move; buy if below.
- Priced at bid on entry and ask on the reaction day (reverse for buys)

## Kill Criterion
- trading is killed if no rule has a postive mean P&L after costs with t > 2 and a linear model's out of sanple R^2 <= 0. If killed, the projects continues as a forecasting-only paper

## Current Decisions
