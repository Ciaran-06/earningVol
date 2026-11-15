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