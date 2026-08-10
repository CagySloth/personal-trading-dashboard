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
