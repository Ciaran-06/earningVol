# Methods - Last Updated: 15/11/26

## 1. Data Sample

### Source
We used end-of-day data from IVolatility (Builder plan) covering 2004-01-02 to 2026-11-03. Data covers stock prices, earnings calendars, IVX, and option chains.

### Universe
- **Current members:** S&P 500 constituents from Wikipedia.
- **Former members:** 409 companies that left the index since 2004, from a daily membership history on GitHub.
- **Option chains:** 49 large-cap names. Chains cover every trading day for NVDA from 2015, and the last close before and first close after each earnings report for the rest, from 2010.
- **Reason for 49 names:** Option chains are the largest download: about 4 API calls per event. Covering every S&P 500 member from 2010 would need roughly 128,000 calls, over six months of the plan's quota. 49 liquid large-caps keep spreads realistic and fit within one month.

### Event count
- Calendar events: 48,035
- Events after merging with prices: 44,085
- Events dropped: 3,950 (see DATA.md for the full breakdown)

### Why events were dropped
- Reaction day after the last price date: 22
- Company has no prices: 536
- Event before the company's first price: 668
- Event after the company's last price: 2,724
- Missing price inside the date range: 1
- These sum to 3,951 because one event fails two checks (beyond the data *and* missing a price).
- *Reason:* a move cannot be measured without both prices, so these events are dropped rather than filled.

### Known limitation
The sample is not point-in-time. Current members keep full history, including years before they joined the index, and the 49-name chain universe is today's large caps, which biases straddle results toward past winners. The first goal was to build and verify the full pipeline (timing, prices, straddles, target) on a manageable sample. A point-in-time universe (the top ~150 by market cap at each date) is planned for the next download cycle and is needed before any final result.

## 2. Event Timing

**Step 1: Trading calendar.** We used the dates on which SPY traded. SPY trades on every US market day and has complete history, so its dates give a clean exchange calendar without needing a separate holiday list.

**Step 2: Reaction day.**
- BMO reports: first trading day on or after the report date.
- AMC reports: first trading day after the report date.
- *Reason:* a BMO report moves the price on the report day; an AMC report moves it the next day. A one-day error would measure an ordinary day instead of the earnings jump.

**Step 3: Entry day.** The trading day before the reaction day.
- *Reason:* it is the last close before the news, so it is a price a trader could act on, and it is when the straddle is opened.

**Step 4: Weekend and holiday reports.** Handled by the same search on the trading calendar.
- *Reason:* the rule rolls non-trading-day reports forward without a special case.

**Step 5: Drop events outside the data.** Reaction day after the last date, or entry day before the first.
- *Reason:* there are no prices to measure them with.

**Step 6: Attach prices.** Entry day: split-adjusted close and unadjusted close. Reaction day: open and close.
- *Reason:* split-adjusted closes keep returns correct across splits. Unadjusted prices are kept for strikes, because historical strikes are not adjusted.

**Step 7: Verification.** A median absolute-return test around the reaction day shows the spike on day 0 (0.0300) against about 0.010 on surrounding days, and two named events (NVDA 2023-05-24, NFLX 2022-04-19) line up.
- *Reason:* a one-day error would move the spike to day −1 or +1, so this test catches timing mistakes directly.

## 3. Moves and Historical Benchmark

**Notation.** Company $i$, event $j$ (its $j$-th earnings event in the data, counted in date order). $C^{\text{entry}}_{i,j}$ is the split-adjusted close on the entry day; $O^{\text{react}}_{i,j}$ and $C^{\text{react}}_{i,j}$ are the split-adjusted open and close on the reaction day.

**Step 1: Log move (`r_event`).**
$$r_{i,j} = \log\left(\frac{C^{\text{react}}_{i,j}}{C^{\text{entry}}_{i,j}}\right)$$
- *Reason:* log returns add up over time and are the standard in volatility modelling, so this is the version used for vol features. The target uses the simple move (Step 3).

**Step 2: Overnight gap (`gap`).**
$$g_{i,j} = \log\left(\frac{O^{\text{react}}_{i,j}}{C^{\text{entry}}_{i,j}}\right)$$
- *Reason:* separates the overnight jump on the news from the trading during the reaction day, so later work can check how much of the move happens at the open.

**Step 3: Simple absolute move (`abs_move_simple`).**
$$m_{i,j} = \left|\frac{C^{\text{react}}_{i,j}}{C^{\text{entry}}_{i,j}} - 1\right|$$
- *Reason:* a straddle pays $|S - K|$, which is a simple price change, so any comparison with option prices must use the simple move.
- *Check:* NVDA 2023-05-24 gives $m = 0.244$ against $|r| = 0.218$. The gap between the two grows with the size of the move, so it matters most on the large moves that drive straddle P&L.

**Step 4: Historical-average move, benchmark B (`hist_move_8`).**
$$B_{i,j} = \frac{1}{8}\sum_{k=1}^{8} m_{i,\,j-k}$$
with $B_{i,j}$ left undefined (NaN) when company $i$ has fewer than 8 earlier events ($j \le 8$).
- *Reason, previous events only:* the sum stops at $j-1$, so the event never enters its own benchmark and no future information is used.
- *Reason, all 8 required:* a short history, such as one that restarts at a ticker rename, is not passed off as a full one.
- *Reason, 8 events:* companies report quarterly, so 8 events cover about two years. That is long enough to average out one unusual quarter, and short enough to follow changes in how much a company typically moves.
- *Limitation:* the window counts events, not time. If events are missing from the middle of a company's history, the 8 events stretch over more than two years.
- *Check:* 5,024 events are NaN, about the first 8 of each company. NVDA 2023-05-24 gives $B = 0.05725$, identical to a hand-computed mean of its previous 8 moves.

## 4. Straddles

Straddles are built only for the 49 companies with option chains.

**Notation.** $S$ = spot on the entry day, $K$ = strike, $T$ = expiry date. $C$ and $P$ are the call and put prices; subscripts bid, mid and ask give the quote, with mid $= (\text{bid} + \text{ask})/2$.

**Step 1: Restrict the chains to event days.** Only chain rows dated on an event's entry or reaction day are kept (9,636,100 → 5,525,302 rows).
- *Reason:* the straddle is only priced on those two days.

**Step 2: Spot.** $S$ is the chain's underlying price on the entry day. If a day's chain shows more than one spot value, the event is skipped.
- *Reason:* strikes are real historical strikes, so they must be compared with the real traded price. The chain's own underlying price is the price the option quotes were taken against, and it equals the unadjusted close.

**Step 3: Expiry.** $T$ is the earliest expiry on or after the reaction day.
- *Reason:* an option that expires before the reaction day is gone before the move happens. The earliest valid expiry carries the least time value unrelated to earnings.

**Step 4: Usable quotes.** A contract is usable if its bid is above zero and its own implied volatility (`preiv`, solved from that contract's price) exists. A strike is kept only if both its call and its put are usable.
- *Reason:* a zero bid means no one is buying, so the contract cannot be sold. An interpolated IV is not a price anyone quoted. A straddle needs both legs, so a strike with one dead leg cannot be traded.

**Step 5: Strike.** $K$ is the usable strike closest to $S$; ties go to the lower strike.
- *Reason:* an at-the-money straddle bets on the size of the move, not its direction. The further $K$ is from $S$, the more the position also bets on direction.

**Step 6: Entry prices and implied move.**
$$\text{straddle}_{\text{bid}} = C_{\text{bid}} + P_{\text{bid}}, \quad \text{straddle}_{\text{mid}} = C_{\text{mid}} + P_{\text{mid}}, \quad \text{straddle}_{\text{ask}} = C_{\text{ask}} + P_{\text{ask}}$$
$$M^{\text{imp}} = \frac{\text{straddle}_{\text{mid}}}{S}, \qquad \text{strike gap} = \frac{K - S}{S}$$
- *Reason:* at expiry the straddle pays $|S_T - K|$. With $K \approx S$, that payoff divided by $S$ is the simple absolute move $m$ from §3. The straddle's price as a fraction of spot is therefore the market's expected absolute move, directly comparable with $m$. The mid is used as the fair-value estimate; the bid and ask are kept for pricing trades.

**Step 7: Exit.** The same expiry and strike are priced at the reaction-day close, with no quote filter.
- *Reason:* at exit you hold a specific contract and cannot switch to a better-quoted one, so whatever quote exists is the price you face.

**Step 8: Outcome.** Each chain-company event records a status.

| Status | Events |
|---|---|
| ok | 3,239 |
| no chain on entry day | 988 |
| no valid strike | 4 |
| no exit quote | 2 |
| **Total (chain-company events)** | **4,233** |

Of the 988 events with no entry-day chain, 982 are from 2004–2009, before chains were downloaded. Of the 3,239 `ok` events, 2,665 are before 2024 and 574 are in the holdout.
- *Check:* NVDA 2023-05-24: $T$ = 2023-05-26, $K = 305$, $S = 305.38$, straddle 21.25 / 21.83 / 22.40, $M^{\text{imp}} = 0.0715$. Exit spot 379.80, exit straddle 73.96 / 74.67 / 75.37, close to the intrinsic value $|379.80 - 305| = 74.80$.
- *Summary:* median $M^{\text{imp}}$ = 4.0%; median entry bid–ask spread = 6.6% of the straddle mid.

**Limitations.**
- $M^{\text{imp}}$ also prices the ordinary trading days between the reaction day and expiry, not only the earnings move. Before weekly options (roughly 2015 for most names) this could be up to a month. It inflates $M^{\text{imp}}$, lowers the move ratio, and makes selling look better than it is.
- There is no fallback expiry: if the earliest expiry has no usable strike, the event fails (4 events).
- The entry filter checks the bid, not that ask ≥ bid. One crossed quote each is known in TSLA and JPM.

## 5. Target

**Step 1: Floor the move.**
$$\tilde m_{i,j} = \max(m_{i,j},\ 0.001)$$
- *Reason:* a zero move would give $\log 0 = -\infty$. Zero moves are floored, not dropped: they are the best outcome for a seller, so dropping them would bias the sample against selling.

**Step 2: Move ratio and target.**
$$\text{ratio}_{i,j} = \frac{\tilde m_{i,j}}{M^{\text{imp}}_{i,j}}, \qquad y_{i,j} = \log(\text{ratio}_{i,j})$$
Computed for `ok` events only; NaN elsewhere.
- *Reason, ratio:* it compares the realised move with the move the options priced in. A ratio above 1 means the stock moved more than priced (good for a buyer), below 1 less (good for a seller).
- *Reason, log:* on the ratio scale, "twice as big" (2) and "half as big" (0.5) sit at unequal distances from 1. On the log scale they sit at $+0.69$ and $-0.69$, symmetric around 0. The log also pulls in very large ratios, so a few huge moves do not dominate a regression.

**Checks.**
- 67 `ok` events (2.1%) are floored, giving $y \approx -3.7$.
- Median ratio 0.70, and 34% of events are above 1. The stock usually moves less than the options price in (the variance risk premium), but a third of the time it moves more.
- NVDA 2023-05-24: ratio $= 0.244 / 0.0715 = 3.41$, $y = 1.227$.

**Limitations.**
- The floored events form a cluster in the left tail of $y$. A robustness check with a 0.05% floor is planned.
- The target uses the mid price. Trades are priced at bid and ask (see NOTES.md), so a forecastable $y$ is not automatically a profitable one.

## 6. Market Cap

**Step 1: Split correction (`market_cap_corr`).**
$$\text{cap}^{\text{corr}}_{i,j} = \text{cap}_{i,j} \times \frac{C^{\text{unadj}}_{i,j}}{C^{\text{entry}}_{i,j}}$$
where $C^{\text{unadj}}$ is the unadjusted entry-day close and $C^{\text{entry}}$ the split-adjusted one.
- *Reason:* the calendar's market cap is the split-adjusted price times the share count at the time, so it is understated by every later split. The ratio of unadjusted to adjusted close is exactly the later-split factor, so multiplying by it restores the true cap. The entry day is used because it is the last close before the news.
- *Check:* AAPL 2004-01-14: factor 56 (Apple's later splits, $2 \times 7 \times 4$), corrected cap \$8.74B. NVDA 2023-05-24: factor 10, \$757B. 2026 events: factor 1.

**Step 2: Last known cap (`market_cap_prev`).** For each event, the most recent `market_cap_corr` from an **earlier** event of the same company, carried forward over missing values. It never fills backward in time or across companies.
- *Reason:* for a BMO report, the event's own cap may already include that day's reaction, so it is not known at entry. A cap one or a few quarters old is close enough for ranking companies by size. This is the version used for ranking and features.
- *Check:* `market_cap_corr` is missing on 4,880 events (11%, spread evenly across years). After carrying forward, `market_cap_prev` is missing on 1,241: each company's events before its first known cap, plus the 22 companies with no cap at all.

**Limitation.** 22 companies have no cap on any event, including BRK_B, which is always among the largest companies. Its treatment in the point-in-time universe is still to be decided.

## 7. Sample Labels and Splits

- `has_chains`: the company is one of the 49 chain names. This is a company-level label; whether a given event has a usable straddle is recorded by `straddle_status`.
- `is_holdout`: report date on or after 2024-01-01 (6,110 events, 13.9%; 574 `ok` straddle events).
- *Reason:* the holdout is fixed by date before any modelling and stays untouched until the final evaluation, so the final result is not tuned to it. A date split, rather than a random one, matches how a forecast would be used: trained on the past, applied to the future.