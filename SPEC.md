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