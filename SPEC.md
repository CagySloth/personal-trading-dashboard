# Milestone 1 Spec: Single-Ticker End-to-End Loop

## Goal
Prove the full pipeline works for ONE ticker before adding any breadth:
fetch → SQLite → FastAPI endpoint → chart render.

## Explicitly out of scope for this milestone
- Multiple tickers / watchlist
- Any indicators (moving averages, RSI, etc.)
- Scheduling / cron / automated fetch cadence
- Authentication
- Styling polish on the frontend

Do not add any of the above even if it seems easy or natural — this
milestone is done when the thin slice works, not when it's feature-rich.

## Ticker
Use SPY for all development and testing.

## Steps

1. **Backend scaffold** (`backend/`)
   - Python, FastAPI
   - SQLite database file (gitignored, not committed)
   - Two tables only: `tickers` (id, symbol) and `daily_prices`
     (ticker_id, date, open, high, low, close, volume)

2. **Fetch script** (`backend/fetch.py` or similar)
   - Standalone script, run manually (not scheduled yet)
   - Uses `yfinance` to pull daily OHLCV history for SPY
   - Writes to SQLite, upserting so re-running doesn't create duplicate
     rows for the same ticker+date

3. **API endpoint**
   - `GET /prices/{ticker}` returns cached OHLCV as JSON from SQLite
   - No other endpoints yet

4. **Frontend** (`frontend/`)
   - Minimal page using `lightweight-charts`
   - Renders a candlestick chart for SPY by calling the `/prices/SPY`
     endpoint
   - No sidebar, no navigation, no extra UI

5. **Verify end to end**
   - Run the fetch script
   - Confirm rows land correctly in SQLite
   - Confirm the API returns them correctly
   - Confirm the chart renders correctly in a browser

## Definition of done
I can run the fetch script, start the backend, open the frontend, and see
a real SPY daily candlestick chart sourced from my own SQLite database.
Nothing more.


# Milestone 2 Spec: Single Indicator Overlay (SMA)

## Context
Milestone 1 is complete: SPY daily candles flow end to end from yfinance
→ SQLite → FastAPI → lightweight-charts. This milestone adds exactly one
indicator on top of that working slice. Do not touch the milestone 1
pipeline except where explicitly described below.

## Goal
Add a Simple Moving Average (SMA) overlay to the existing SPY chart,
computed from data already cached in SQLite. No new data source is needed
for this milestone.

## Explicitly out of scope for this milestone
- Any indicator other than SMA (no RSI, MACD, Bollinger Bands, etc.)
- Multiple tickers / watchlist
- Indicator selection UI (dropdowns, toggles, multiple windows at once)
- Scheduling / cron / automated fetch cadence
- Authentication
- Styling polish beyond what's needed to see the overlay clearly

Do not add any of the above even if it seems easy or natural — this
milestone is done when the SMA line renders correctly on the existing
chart, not when it's feature-rich.

## Ticker
Continue using SPY.

## Design decisions (already made — don't re-litigate these)
- **Indicator**: Simple Moving Average, not EMA or anything smoothed.
  Simplest to compute and easiest to verify by hand.
- **Default window**: 20-day, but implement it as a parameter, not a
  hardcoded constant, so other windows can be requested later.
- **API shape**: extend the existing `GET /prices/{ticker}` endpoint with
  an optional query parameter (e.g. `?sma=20`) rather than adding a
  separate endpoint. One endpoint to maintain instead of two.
- **Where SMA is computed**: in the backend, from data already in
  `daily_prices`. No new fetch logic, no new external API calls.

## Steps

1. **SMA calculation function** (backend)
   - A function that takes a list/series of daily closes and a window
     size, and returns the SMA series (same length as input, with `null`
     or omitted values for the initial period shorter than the window).
   - Pure function, no I/O — should be straightforward to unit-test by
     hand-checking a few values.

2. **Extend the API endpoint**
   - `GET /prices/{ticker}?sma=20` returns the existing OHLCV payload
     plus an `sma` field per row (or a parallel array — your call on
     shape, just keep it consistent).
   - If `sma` query param is omitted, behavior is unchanged from
     milestone 1 (no SMA data returned).
   - Window size in the query param is configurable, not hardcoded to 20
     server-side — 20 is just the default if the frontend requests it
     with no explicit window elsewhere.

3. **Frontend overlay**
   - Add a line series to the existing candlestick chart using
     lightweight-charts' multi-series support.
   - Request SMA data via the extended endpoint (default window 20).
   - Line should render clearly distinguishable from the candlesticks
     (e.g. a distinct color), no legend/UI controls needed yet.

4. **Verify end to end**
   - Pick 2-3 dates on the chart and hand-check the SMA value against a
     manual calculation (e.g. average the last 20 closes yourself in a
     spreadsheet or by eye) to confirm the backend math is correct.
   - Confirm the line renders in the right place relative to price (SMA
     should visually lag price and smooth out day-to-day noise).
   - Confirm omitting `?sma=` still returns plain milestone-1 behavior
     (nothing broke).

## Definition of done
The SPY chart shows candlesticks with a 20-day SMA line overlaid,
computed server-side from cached data, verified correct against a manual
spot-check. The `/prices/{ticker}` endpoint works both with and without
the `sma` parameter. Nothing else changed.

# Milestone 3 Spec: Watchlist (Multiple Tickers)

## Context
Milestone 1 (single-ticker end-to-end loop) and Milestone 2 (SMA overlay)
are complete. SPY currently flows: yfinance → SQLite → FastAPI →
lightweight-charts, with a 20-day SMA overlay. This milestone generalizes
the pipeline from one hardcoded ticker to a small set of tickers the user
can switch between. Do not touch the SMA logic itself except where it
needs to work per-ticker instead of SPY-only.

## Goal
Support multiple tickers end to end: stored in SQLite, fetchable via a
script that loops over them, selectable from the frontend, each rendering
its own chart + SMA overlay correctly.

## Explicitly out of scope for this milestone
- Configurability of indicators (colors, parameters, settings UI) — this
  is intentionally deferred to a later milestone once there's more than
  one indicator to design the config system against. Do not build a
  settings/preferences layer, color picker, or parameter UI here.
- Any indicator other than the existing SMA
- Scheduling / cron / automated fetch cadence — fetch script remains
  manual/on-demand
- Authentication
- Alerts, news feed, or any feature beyond ticker selection + chart
- Styling polish beyond a simple, functional way to pick a ticker

Do not add any of the above even if it seems easy or natural — this
milestone is done when ticker switching works correctly, not when it's
feature-rich.

## Starter tickers
Seed the `tickers` table with: **SPY, AAPL, QQQ**. This just needs to
prove "more than one ticker works," not be a final watchlist — more can
be added later by inserting rows, without code changes.

## Design decisions (already made — don't re-litigate these)
- Ticker list lives in the existing `tickers` table (already created in
  Milestone 1) — no new table needed.
- Fetch script changes from "hardcoded SPY" to "loop over all rows in
  `tickers`," still run manually, not scheduled.
- Frontend ticker selection can be as simple as a dropdown or basic list
  — no design polish expected here.

## Steps

1. **Seed the tickers table**
   - Insert SPY, AAPL, QQQ into `tickers` (via the fetch script itself,
     a small seed script, or a one-time manual insert — your call).

2. **Update the fetch script**
   - Instead of pulling one hardcoded symbol, loop over every row in
     `tickers` and fetch/upsert daily OHLCV for each into `daily_prices`,
     same upsert logic as Milestone 1 (no duplicate rows on re-run).

3. **Add a tickers-list API endpoint**
   - `GET /tickers` returns the list of available tickers (symbol, and
     id if useful) so the frontend knows what it can offer for
     selection.
   - Existing `GET /prices/{ticker}?sma=20` endpoint stays as is — it
     already takes a ticker parameter, so no change needed there beyond
     confirming it works correctly for AAPL and QQQ too, not just SPY.

4. **Frontend ticker selection**
   - Add a simple selector (dropdown is fine) populated from `GET
     /tickers`.
   - Selecting a ticker re-fetches `/prices/{ticker}?sma=20` for that
     symbol and re-renders the chart (candles + SMA line) for it.
   - Default to one ticker (e.g. SPY) on initial page load.

5. **Verify end to end**
   - Run the updated fetch script; confirm all three tickers land
     correctly in `daily_prices` with no duplicates on re-run.
   - Confirm `GET /tickers` returns all three.
   - Confirm switching the selector between SPY, AAPL, and QQQ shows the
     correct chart and correct SMA line for each — spot-check at least
     one non-SPY ticker's SMA value by hand, same as Milestone 2's
     verification approach.
   - Confirm adding a fourth ticker directly to the `tickers` table (no
     code change), then re-running the fetch script, makes it appear as
     selectable in the frontend.

## Definition of done
The dashboard offers SPY, AAPL, and QQQ as selectable tickers. Choosing
any of them shows the correct candlestick chart with a correct 20-day SMA
overlay, sourced from SQLite. The fetch script populates all tickers in
the table, not just one. Adding a new ticker to the table and re-running
the fetch script makes it selectable without any code changes. No
indicator configuration UI, scheduling, or other out-of-scope features
were added.

# Milestone 4 Spec: Second Indicator (RSI)

## Context
Milestones 1-3 are complete: multiple tickers (SPY, AAPL, QQQ) flow end to
end from yfinance → SQLite → FastAPI → lightweight-charts, with a
selectable ticker and a 20-day SMA overlay on the price chart. This
milestone adds a second, structurally different indicator: RSI (Relative
Strength Index). Do not touch the existing SMA logic or the ticker
selection built in Milestone 3.

## Goal
Add RSI as a second indicator, rendered in its own chart panel below the
existing candlestick chart, computed server-side from data already in
SQLite. No new data source needed.

## Explicitly out of scope for this milestone
- Indicator configuration / settings UI (colors, parameter editing,
  persistence of user preferences) — still intentionally deferred. This
  milestone exists partly to reveal what a future config system needs to
  support (RSI has more parameters and a different rendering shape than
  SMA), but do not build the config system itself yet.
- Any indicator other than SMA and RSI
- Scheduling / cron / automated fetch cadence
- Authentication
- Alerts, news feed, or anything beyond the two indicators
- Styling polish beyond what's needed for RSI to be clearly readable in
  its own panel

Do not add any of the above even if it seems easy or natural.

## Ticker
Works across all tickers already in the watchlist (SPY, AAPL, QQQ) — RSI
should follow the same per-ticker selection behavior as SMA, not be
SPY-only.

## Design decisions (already made — don't re-litigate these)
- **Default window**: 14-day, implemented as a parameter (same pattern as
  SMA's window), not hardcoded.
- **Default thresholds**: 70 (overbought) / 30 (oversold), the
  conventional values. Also implement as parameters, not hardcoded, even
  though the config UI to change them doesn't exist yet — same "make it a
  parameter now, expose it later" approach used for SMA's window.
- **Smoothing method**: use Wilder's smoothing (the standard RSI
  calculation), not a naive simple-average approximation. RSI computed
  with the wrong smoothing method gives materially different values, so
  this is worth doing correctly the first time rather than approximating.
- **API shape**: extend the existing `GET /prices/{ticker}` endpoint
  further, e.g. `?rsi=14`, independently of `?sma=20` — both should be
  usable together or separately. Consistent with the pattern from
  Milestone 2, not a new endpoint.
- **Rendering**: RSI renders in its own panel/pane below the price chart,
  not overlaid on candles — different scale (0-100) makes an overlay
  meaningless. Check lightweight-charts' mechanism for synchronized
  multi-pane charts during implementation.

## Steps

1. **RSI calculation function** (backend)
   - Pure function: takes a series of closes and a window size, returns
     an RSI series (0-100) using Wilder's smoothing method.
   - No I/O — should be straightforward to hand-verify against a few
     manually calculated values.

2. **Extend the API endpoint**
   - `GET /prices/{ticker}?sma=20&rsi=14` returns OHLCV plus SMA plus RSI
     values, each independently optional via its own query param.
   - Omitting `rsi` preserves current (Milestone 1-3) behavior exactly.

3. **Frontend RSI panel**
   - Add a second chart pane below the existing candlestick + SMA chart,
     synchronized on the same time axis.
   - Render the RSI line in that pane, scaled 0-100.
   - Add reference lines (or equivalent) at the 70 and 30 thresholds so
     overbought/oversold zones are visually identifiable.
   - RSI panel updates correctly when the ticker selector changes,
     matching the selected ticker's data.

4. **Verify end to end**
   - Hand-check RSI values against a manual Wilder's-smoothing
     calculation on 2-3 dates for at least one ticker.
   - Confirm the RSI panel is time-synchronized with the price chart
     above it (same date range, aligned).
   - Confirm switching tickers updates both panels correctly.
   - Confirm requesting `?sma=20` without `?rsi=14` (and vice versa)
     still works independently — the two indicators don't depend on each
     other.

## Definition of done
Selecting any of the three watchlist tickers shows the candlestick chart
with SMA overlay (as before) plus a new RSI panel below it, using a
14-day window and 70/30 threshold lines, computed correctly via Wilder's
smoothing and verified by hand. The two indicators can be requested
independently via the API. No configuration UI was added — that remains
deferred to a later milestone, now informed by having two structurally
different indicators (overlay-with-one-parameter vs. separate-panel-with-
multiple-parameters) to design against.