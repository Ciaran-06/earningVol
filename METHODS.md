# Methods - Last Updated: 15/11/26

## 1. Data Sample

### Source
We used end-of-day data from IVolatility (Builder plan) covering 2004-01-02 to 2026-11-03. Data covers stock prices, earnings calendars, IVX, and option chains.

### Universe
- **Current members:** S&P 500 constituents from Wikipedia.
- **Former members:** 409 companies that left the index since 2004, from a daily membership history on GitHub.
- **Option chains:** 49 large-cap names. Chains cover every trading day for NVDA from 2015, and the last close before and first close after each earnings report for the rest, from 2010.
- **Reason for 49 names:** Option chains are the largest download: about 4 API calls per event. Covering every S&P 500 member from 2010 would need roughly 128,000 calls, over six months of the plan’s quota. 49 liquid large-caps keep spreads realistic and fit within one month.

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

--- 