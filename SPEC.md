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

# Milestone 5 Spec: Indicator Configuration Layer

## Context
Milestones 1-4 are complete: multi-ticker (SPY, AAPL, QQQ) dashboard with
a candlestick chart, a 20-day SMA overlay, and a 14-day RSI panel with
70/30 threshold lines. All indicator parameters (SMA window, RSI window,
RSI thresholds) are currently hardcoded defaults passed as function/API
parameters, but there is no way for the user to change them without
editing code. This milestone adds that configuration layer.

## Goal
Let the user change indicator parameters (windows, thresholds) and line
colors, persist those choices in SQLite, and have the dashboard use the
saved values instead of hardcoded defaults — across restarts, not just
within one session.

## Explicitly out of scope for this milestone
- Per-ticker configuration — settings are global (apply the same
  regardless of which ticker is selected), not per-symbol. This may
  change in a future milestone but is out of scope now.
- Saved presets or multiple named configurations — one active global
  config, no "save as" / switch-between-configs functionality.
- Any indicator other than SMA and RSI
- Line style/thickness or other visual properties beyond color — color
  only for this pass.
- Scheduling / cron / automated fetch cadence
- Authentication
- Alerts, news feed, or anything unrelated to indicator configuration

Do not add any of the above even if it seems easy or natural — this
milestone is done when SMA and RSI's existing parameters and colors are
configurable and persisted, nothing more.

## Design decisions (already made — don't re-litigate these)
- **Scope of settings**: global, not per-ticker.
- **What's configurable**: for SMA — window size, line color. For RSI —
  window size, overbought threshold, oversold threshold, line color.
- **Persistence**: a new SQLite table (e.g. `indicator_settings`), not
  browser localStorage — keeps settings available from any device later
  (relevant to the eventual iPhone-access goal), and consistent with
  "don't lose state on restart" already used for price data.
- **Defaults**: if no settings row exists yet (first run), fall back to
  the current hardcoded defaults (SMA 20, RSI 14/70/30, some reasonable
  default colors) rather than erroring.

## Steps

1. **Settings table** (backend)
   - New SQLite table, e.g. `indicator_settings`, holding one row (global,
     not per-ticker) with columns for: `sma_window`, `sma_color`,
     `rsi_window`, `rsi_overbought`, `rsi_oversold`, `rsi_color`.
   - On first run, if no row exists, seed it with current defaults
     (20 / some color, 14 / 70 / 30 / some color).

2. **Settings API endpoints**
   - `GET /settings` returns the current indicator settings.
   - `PUT /settings` (or `POST`) updates them, replacing the stored
     values. Validate reasonable ranges server-side (e.g. window > 0,
     0 < oversold < overbought < 100 for RSI) and return a clear error
     if invalid — don't let bad values silently corrupt the chart.

3. **Wire existing endpoints to use stored settings**
   - `GET /prices/{ticker}` — when `sma` or `rsi` query params are used
     without explicit values (or if you simplify to always use stored
     settings when the indicator is requested), pull window/threshold
     values from `indicator_settings` instead of hardcoded constants.
   - Decide and document whether query params can still override stored
     settings per-request, or whether stored settings are now the single
     source of truth. Either is fine — just be explicit about which.

4. **Frontend settings UI**
   - A simple settings panel or modal (doesn't need to be visually
     polished) with: number input for SMA window, color picker for SMA
     line, number inputs for RSI window/overbought/oversold, color picker
     for RSI line.
   - Saving calls `PUT /settings` and then re-renders the chart using the
     new values — no page reload required.
   - Panel pre-populates from `GET /settings` on load, showing current
     (not hardcoded) values.

5. **Verify end to end**
   - Change SMA window and color via the UI; confirm the chart updates
     to reflect both.
   - Change RSI window and thresholds; confirm the RSI panel and its
     70/30-equivalent reference lines update to match the new values.
   - Restart the backend and reload the frontend; confirm settings
     persisted (not reset to hardcoded defaults).
   - Submit an invalid value (e.g. RSI oversold > overbought) and confirm
     it's rejected with a clear error, not silently accepted.
   - Confirm settings apply consistently across all three tickers
     (global, not per-ticker, as scoped).

## Definition of done
The user can open a settings panel, change SMA's window/color and RSI's
window/thresholds/color, save them, and see the chart update accordingly
— for any ticker in the watchlist. Settings persist across a backend
restart. Invalid values are rejected, not silently applied. Per-ticker
settings, saved presets, and additional visual properties remain
deferred to future milestones.

# Milestone 6 Spec: Scheduled Fetch Job

## Context
Milestones 1-5 are complete: multi-ticker (SPY, AAPL, QQQ) dashboard with
SMA overlay and RSI panel, both configurable via a settings layer
persisted in SQLite. Data freshness currently depends on the user
manually re-running the fetch script — there is no automated refresh.
This milestone automates that, still using daily candles only. It does
not add live/intraday quotes (Finnhub WebSocket) or a timeframe selector
(1min/5min/etc.) — both are explicitly separate, later milestones that
depend on this one being done first.

## Goal
The existing fetch script (which already loops over all tickers in the
`tickers` table, per Milestone 3) runs automatically on a schedule
instead of only when manually triggered, so cached data stays current
without the user having to remember to run it.

## Explicitly out of scope for this milestone
- Live/intraday quotes via Finnhub WebSocket — separate milestone
- Timeframe selection (1min/5min/etc.) — separate milestone, and
  depends on this one being done first
- Any change to indicator logic, settings, or the frontend chart itself
- Authentication
- Alerts, news feed, or anything unrelated to fetch scheduling
- Notifications/logging dashboards beyond basic console/log output for
  verifying the job ran

Do not add any of the above even if it seems easy or natural — this
milestone is done when the existing fetch logic runs on a schedule
reliably, nothing more.

## Design decisions (already made — don't re-litigate these)
- **Cadence**: once daily, after US market close, is the default target
  for this milestone. (If a more frequent EOD-safe cadence, e.g. every
  few hours during market hours re-pulling the latest daily bar, is
  trivial given the chosen scheduling approach, that's acceptable too —
  but don't build intraday-resolution polling here; that's the deferred
  Finnhub/timeframe work.)
- **Mechanism**: an in-process scheduler (e.g. APScheduler in Python)
  running inside the existing FastAPI backend, rather than a separate
  system-level cron job. Keeps the scheduling logic inside the app and
  version-controlled with the rest of the code, rather than depending on
  OS-level configuration that isn't captured in the repo.
- **Reuse, don't rewrite**: the scheduled job calls the same fetch logic
  already built in Milestone 3 (loop over `tickers`, upsert into
  `daily_prices`) — this milestone is about *when* it runs, not changing
  *what* it does.
- **Failure handling**: if a fetch for one ticker fails (e.g. yfinance
  hiccup, network issue), it should not crash the scheduler or block
  other tickers from being fetched — log the failure and continue.

## Steps

1. **Add scheduler to the backend**
   - Integrate an in-process scheduler into the FastAPI app, configured
     to run the existing fetch-all-tickers logic once daily after market
     close (exact time is flexible — e.g. 4:30pm ET as a reasonable
     default, adjust if needed).
   - Scheduler starts when the backend starts, stops cleanly when the
     backend stops — no orphaned background processes.

2. **Error handling per ticker**
   - Wrap each ticker's fetch in error handling so one failure (bad
     symbol, network blip, yfinance hiccup) doesn't stop the rest of the
     batch from running.
   - Log failures clearly (which ticker, what error) so they're visible,
     even if just to console/log file for now.

3. **Manual trigger endpoint (for testing and convenience)**
   - Add a `POST /fetch/run` endpoint (or similar) that triggers the same
     fetch job on demand, independent of the schedule — useful for
     testing without waiting for the scheduled time, and as a manual
     "refresh now" option going forward.

4. **Verify end to end**
   - Confirm the scheduler is registered and running when the backend
     starts (check logs/startup output).
   - Trigger the job manually via the new endpoint and confirm all three
     tickers update correctly in `daily_prices`, with the existing
     upsert logic preventing duplicates.
   - Simulate a failure for one ticker (e.g. temporarily use an invalid
     symbol) and confirm the other tickers still fetch successfully and
     the failure is logged, not silently swallowed or crash-inducing.
   - Leave the backend running past the scheduled time (or temporarily
     set it to a near-future time for testing) and confirm the job fires
     automatically without manual intervention.

## Definition of done
The backend automatically refreshes daily price data for all watchlist
tickers on a schedule, without requiring the user to manually run the
fetch script. A manual trigger endpoint exists for on-demand refresh. A
single ticker's fetch failure doesn't block the others or crash the
scheduler. Live/intraday quotes and timeframe selection remain deferred
to their own future milestones.

# Milestone 7 Spec: Startup Staleness Check

## Context
Milestone 6 added a scheduled fetch job (daily, in-process scheduler) plus
a manual `POST /fetch/run` trigger endpoint. That scheduler only fires if
the backend happens to be running at the scheduled time. Since this app
runs locally rather than as an always-on server, the backend is often
*not* running at that time (laptop asleep, app not launched, etc.), so
scheduled runs can be silently missed with nothing catching up the gap.
This milestone adds a startup check that detects stale data and triggers
a catch-up fetch automatically, without waiting for the next scheduled
time.

## Goal
Every time the backend starts, it checks whether cached price data is
stale (older than the last completed trading day) and, if so, triggers
the existing fetch job immediately — so opening the dashboard after any
gap (a day, a weekend, a week) reliably shows current data without the
user needing to manually trigger a refresh.

## Explicitly out of scope for this milestone
- Any change to the daily scheduled job itself (still runs as configured
  in Milestone 6) — this milestone adds a startup check alongside it, not
  a replacement
- Live/intraday quotes (Finnhub WebSocket) — still deferred
- Timeframe selection — still deferred, and still depends on this
  freshness work being solid first
- Any frontend changes beyond an optional simple loading/status indicator
  (see Step 3) — no new UI features
- Retrying failed catch-up fetches on a sub-schedule (e.g. retry every 5
  minutes until success) — out of scope, one attempt on startup is enough
  for this milestone

Do not add any of the above even if it seems easy or natural.

## Design decisions (already made — don't re-litigate these)
- **Staleness definition**: cached data is "stale" if the most recent
  date in `daily_prices` (check across the watchlist, or just one
  representative ticker — your call, but be consistent) is older than
  the last completed trading day. Simplest correct approach: compare the
  latest cached date against "yesterday" accounting for weekends (don't
  flag Monday morning as stale just because Friday's close is the most
  recent trading day available yet).
- **No need for full market-calendar awareness**: don't build in holiday
  handling for this milestone — weekday-vs-weekend awareness is enough.
  A holiday will just trigger one harmless extra fetch attempt that
  yfinance will handle gracefully (no new data, no error). Not worth the
  complexity of a full trading-calendar dependency right now.
- **Reuse existing fetch logic**: this calls the same fetch-all-tickers
  logic already used by the Milestone 6 scheduler and the `/fetch/run`
  endpoint — no new fetch code, just a new trigger condition.
- **Non-blocking startup**: the staleness check and catch-up fetch should
  not make the backend fail to start or hang indefinitely if the fetch
  is slow or fails — the API should still come up and serve whatever
  cached data exists, with the catch-up fetch happening in the
  background if possible, or with a short reasonable timeout if it needs
  to block.

## Steps

1. **Staleness check function** (backend)
   - A function that reads the most recent cached date from
     `daily_prices` and compares it against the expected latest trading
     day (weekday-aware, per the design decision above), returning
     whether data is stale.

2. **Wire into startup**
   - On backend startup, after the scheduler from Milestone 6 is
     registered, run the staleness check.
   - If stale, trigger the existing fetch-all-tickers job immediately
     (same logic as `/fetch/run`), logging that a catch-up fetch is
     running and why.
   - If not stale, log that data is current and skip the fetch — don't
     fetch unnecessarily on every restart if data's already fresh.

3. **Non-blocking behavior**
   - Ensure this doesn't delay the backend from accepting requests —
     run the catch-up fetch as a background task if your framework
     supports it easily, rather than blocking startup until it
     completes. If a simple blocking call is much easier to implement
     correctly and the fetch is fast enough in practice, that's an
     acceptable tradeoff to flag and confirm rather than over-engineer.

4. **(Optional) simple staleness indicator on the frontend**
   - If straightforward, surface a small, unobtrusive indicator (e.g. "
     data as of [date]" or "refreshing..." text) so the user can tell
     whether they're looking at current or catching-up data. Skip this
     if it adds meaningful complexity — it's a nice-to-have for this
     milestone, not a requirement.

5. **Verify end to end**
   - Stop the backend, manually set/confirm the cached data is a few
     days old (or use existing older data if available), restart the
     backend, and confirm the catch-up fetch fires automatically and
     brings data current — without the user doing anything manually.
   - Restart the backend again immediately after (data now fresh) and
     confirm it correctly skips an unnecessary fetch this time.
   - Confirm the backend still comes up and serves existing cached data
     promptly even if the catch-up fetch is slow or one ticker fails
     (reusing Milestone 6's per-ticker error handling).
   - Confirm the existing daily scheduled job from Milestone 6 still
     fires normally on its own schedule, unaffected by this change.

## Definition of done
Restarting the backend after any gap in uptime (a missed scheduled run,
an overnight shutdown, a week away) automatically catches up stale price
data without manual intervention, while the backend still starts up
promptly and serves existing cached data even if the catch-up fetch is
slow. Data that's already current doesn't trigger an unnecessary fetch.
The Milestone 6 scheduled job continues to work as before, unaffected.

# Milestone 8 Spec: Timeframe Selection

## Context
Milestones 1-7 are complete: multi-ticker dashboard with configurable
SMA/RSI, a daily scheduled fetch job, and a startup staleness check —
all built around a single timeframe (daily candles). This milestone adds
the ability to select a different timeframe (e.g. 1 day, 1 hour, 5
minute) and have the chart and both indicators re-render against that
resolution. This depends on Milestones 6-7 already being solid — do not
start this until scheduled fetch + startup catch-up are confirmed
working, since intraday resolution on top of unreliable freshness isn't
useful.

## Important constraint — read before implementing
yfinance's intraday data availability is limited by Yahoo's own
retention, not by anything you control:
- **1-minute bars**: only the last ~7 days available
- **2m / 5m / 15m / 30m / 60m / 90m**: only the last ~60 days
- **Daily (1d) and above**: full history available

This is a hard ceiling, not something caching or retry logic can work
around. The UI must reflect this — don't let the user request a 1-minute
chart going back 3 months and silently show nothing or an error with no
explanation.

## Goal
Let the user pick a timeframe from a small supported set, see the chart
and both indicators (SMA, RSI) render correctly at that resolution, with
clear handling when a requested range exceeds what that timeframe's data
retention allows.

## Explicitly out of scope for this milestone
- Live/streaming quotes (Finnhub WebSocket) — still a separate,
  independent piece of future work
- Automatically scheduling fetches for every timeframe — intraday
  timeframes are fetched on-demand (see design decisions below), not
  pre-cached on a schedule for all tickers
- Per-ticker default timeframe memory / persisted UI preference — the
  timeframe selector resets to the default (1 day) on page load for now
- Gap-filling, interpolation, or backfilling data beyond what yfinance
  actually provides for a given timeframe
- Any new indicator or change to indicator math itself — SMA/RSI logic
  is reused as-is, just computed against whichever timeframe's bars are
  loaded

Do not add any of the above even if it seems easy or natural.

## Supported timeframe set for this milestone
Start with: **1 day (existing), 1 hour, 5 minute**. Skip 1-minute for
now — its 7-day retention window is narrow enough that it's likely to be
more confusing than useful as a first pass; it can be added later as a
near-trivial extension of this same mechanism once the rest is proven.

## Design decisions (already made — don't re-litigate these)
- **Schema**: generalize the existing `daily_prices` table (or add a
  new, more general `prices` table) with a `timeframe` column, so bars
  of different resolutions coexist rather than needing a separate table
  per timeframe. Decide which approach is less disruptive to existing
  Milestone 1-7 code and take that path — either is acceptable, but
  don't create a proliferation of near-identical tables (one per
  timeframe) if a single table with a `timeframe` column works cleanly.
- **Fetch strategy**: on-demand, not pre-scheduled. When a timeframe is
  requested for a ticker and isn't already cached (or is stale per that
  timeframe's own reasonable freshness expectation — e.g. an hour-old 5m
  cache is stale, an hour-old 1d cache is not), fetch it from yfinance
  at request time, cache the result, then serve it. The existing daily
  scheduled job (Milestone 6) and startup check (Milestone 7) continue
  to apply only to the 1-day timeframe — don't extend them to intraday
  timeframes in this milestone.
- **API shape**: extend `GET /prices/{ticker}` with a `timeframe`
  parameter (e.g. `?timeframe=1d`, default `1d` if omitted, preserving
  all existing behavior exactly). Indicator params (`sma`, `rsi`) work
  the same way regardless of timeframe — they operate on however many
  bars are loaded, whatever the resolution.
- **Out-of-range requests**: if a requested date range exceeds what a
  timeframe supports (e.g. 5-minute bars from 4 months ago), return a
  clear, structured error or a partial result with a clear indicator of
  the actual available range — not a silent empty chart. Pick whichever
  is simpler to implement correctly; just make the limitation visible to
  the frontend so it can inform the user.

## Steps

1. **Schema change** (backend)
   - Add timeframe support to the price-storage schema per the design
     decision above. Migrate existing daily data to fit the new shape if
     the table is restructured, don't lose Milestone 1-7 cached history.

2. **Fetch logic for intraday timeframes**
   - Extend the existing fetch function to accept a timeframe parameter
     and pull the corresponding yfinance interval.
   - Implement on-demand fetch-and-cache: if requested data isn't cached
     or is stale for that timeframe, fetch before responding.
   - Implement clear handling for out-of-range requests per the design
     decision above.

3. **Extend the API endpoint**
   - `GET /prices/{ticker}?timeframe=5m&sma=20&rsi=14` — timeframe
     composes with the existing indicator params, all independently
     optional. Omitting `timeframe` preserves exact current (1-day)
     behavior.

4. **Frontend timeframe selector**
   - Add a simple selector (dropdown, tabs, whatever's straightforward)
     offering 1 day / 1 hour / 5 minute.
   - Changing it re-fetches price + indicator data at the new resolution
     and re-renders both the candlestick chart and the RSI panel.
   - If the backend signals an out-of-range/limited-availability
     response, surface that to the user clearly (e.g. "5-minute data
     only available for the last 60 days") rather than showing a
     confusing empty or broken chart.

5. **Verify end to end**
   - Confirm 1-day behavior is completely unchanged from Milestone 7
     when no timeframe param is passed.
   - Select 1-hour and 5-minute timeframes for at least one ticker;
     confirm bars render at the correct resolution and both SMA and RSI
     recompute correctly against the new bar count (spot-check a value
     by hand, same discipline as prior milestones).
   - Request a 5-minute timeframe with an intentionally too-wide date
     range and confirm the out-of-range handling behaves as designed
     (clear error or clearly bounded partial result), not a silent
     failure.
   - Confirm switching timeframes for a ticker not previously cached at
     that resolution triggers an on-demand fetch and still returns
     correct data (just possibly slower on first request).

## Definition of done
The user can switch between 1 day, 1 hour, and 5 minute timeframes for
any watchlist ticker, with the candlestick chart, SMA, and RSI all
correctly reflecting the selected resolution. Data outside a timeframe's
real availability window is handled visibly, not silently. Existing
1-day behavior, the Milestone 6 schedule, and the Milestone 7 startup
check are all unaffected. 1-minute timeframe, live quotes, and persisted
timeframe preference remain deferred to future milestones.

# Milestone 9 Spec: Minimal Backtesting Engine

## Context
Milestones 1-8 are complete: multi-ticker dashboard with configurable
SMA/RSI indicators and multiple timeframes, backed by a reliable
scheduled + startup-checked fetch pipeline. This milestone is a
deliberate scope shift from "view/analysis" to "simulation" — the first
step toward the longer-term backtesting/algo-strategy goal. It is scoped
as narrowly as Milestone 1 was: one strategy, one ticker, one timeframe,
core simulation logic only. This is intentional. Do not generalize beyond
what's specified below, even though it may seem natural to build a more
flexible engine.

## Goal
Simulate a simple SMA-crossover strategy against cached historical daily
data for one ticker, produce honest performance metrics, and compare the
result against buy-and-hold on the same ticker and period. Prove the
simulation logic is correct before any generalization (multiple
strategies, multiple tickers, cost modeling, etc.).

## Explicitly out of scope for this milestone
- Any strategy other than SMA crossover
- Any ticker other than SPY
- Any timeframe other than daily
- Transaction costs, slippage, fees, or bid-ask spread modeling — this
  milestone assumes frictionless trades, which is a known simplification
  to be corrected in a later milestone, not an oversight
- Position sizing beyond fully-in / fully-out (no partial sizing,
  leverage, or shorting)
- Walk-forward validation, out-of-sample testing, or parameter
  optimization/tuning
- A strategy picker, backtest configuration UI, or equity-curve charting
  — a plain results output (API JSON response, or a simple rendered
  summary) is sufficient for this milestone
- Persisting backtest results to SQLite — compute and return on request,
  no history of past backtest runs needs to be stored yet

Do not add any of the above even if it seems easy or natural — this
milestone is done when the SMA-crossover simulation runs correctly on
SPY daily data and reports honest metrics against a buy-and-hold
comparison, nothing more.

## Strategy definition (already decided — don't re-litigate this)
**SMA crossover, using the existing SMA calculation from Milestone 2:**
- Buy (go fully long) when price closes above the SMA.
- Sell (go fully flat) when price closes below the SMA.
- Use the same SMA window already configured in `indicator_settings`
  from Milestone 5 (default 20-day) — reuse the existing SMA function,
  don't reimplement it.
- Start with 100% cash, no leverage. When a buy signal fires, invest all
  available cash in the ticker. When a sell signal fires, liquidate the
  full position back to cash.
- No trades in between signals — the position just holds until the next
  signal flips it.

## Design decisions (already made — don't re-litigate these)
- **Frictionless assumption**: trades execute at the closing price of
  the signal day, with no costs. This will materially overstate returns
  relative to reality — that's expected and will be addressed by adding
  cost modeling in a future milestone, not this one.
- **Benchmark**: alongside the strategy's results, compute buy-and-hold
  returns for the same ticker over the same exact date range (buy at the
  start, hold through the end, no trading). This is the comparison that
  actually matters — not any external product's marketed performance.
- **Data source**: use the already-cached daily SPY data from SQLite —
  no new fetch logic needed for this milestone.
- **Output shape**: a single API endpoint returning a structured result
  — no need to decide UI/frontend rendering yet.

## Steps

1. **Backtest simulation function** (backend)
   - Pure function: takes a series of daily OHLCV bars (with pre-computed
     SMA values, reusing the existing SMA function) and simulates the
     crossover strategy described above, bar by bar, in chronological
     order.
   - Tracks: cash balance, position (in/out), each trade executed (entry
     date/price, exit date/price), running portfolio value over time.
   - Returns the full trade log and the resulting equity series (even
     though charting it isn't in scope yet — having the series makes
     metrics computation and future charting straightforward).
   - **Important correctness check**: make sure the signal on a given day
     only uses data available up to and including that day — no
     look-ahead (e.g. don't let a signal use a future SMA value that
     wouldn't have been known at the time). This is one of the core
     backtesting pitfalls flagged earlier in this project — verify it
     explicitly, don't assume it's fine because the loop looks
     sequential.

2. **Metrics calculation**
   - From the trade log and equity series, compute: total return (%),
     max drawdown (%), number of trades, win rate (% of trades that were
     profitable).
   - Compute the same total return and max drawdown for buy-and-hold on
     the same ticker/period for comparison.

3. **API endpoint**
   - `GET /backtest/sma-crossover?ticker=SPY` (ticker param present for
     clarity even though SPY is the only supported value right now — do
     not add support for other tickers this milestone).
   - Returns: strategy metrics, buy-and-hold metrics, and the trade log,
     as structured JSON.
   - If requested for a ticker with insufficient cached history to run a
     meaningful backtest (e.g. fewer bars than the SMA window), return a
     clear error rather than a misleading result.

4. **Verify end to end**
   - Hand-check the first 3-5 signals (buy/sell dates) against the
     actual SPY price and SMA data for those dates, confirming the
     crossover logic is triggering correctly and using only
     already-known data (no look-ahead).
   - Confirm the equity series and final total return are internally
     consistent (e.g. manually recompute the return of 1-2 trades from
     the trade log and confirm it matches what's reported).
   - Confirm the buy-and-hold comparison figure is correct for the same
     exact date range the strategy was tested over — same start/end
     dates, not a different or looser range.
   - Run the endpoint on the full available SPY history and sanity-check
     that the numbers are plausible (e.g. don't show a suspiciously
     perfect win rate or return that's an obvious sign of a bug like
     look-ahead bias).

## Definition of done
Calling `GET /backtest/sma-crossover?ticker=SPY` returns a correct trade
log, equity series, and honest performance metrics for the SMA-crossover
strategy on cached SPY daily data, verified by hand against a handful of
real signals, alongside a correctly-computed buy-and-hold comparison over
the identical period. No look-ahead bias in the signal logic. Costs,
other strategies, other tickers, and any UI beyond raw API output remain
deferred to future milestones.

# Milestone 10 Spec: Signal Markers on Chart

## Context
Milestone 9 built a backtesting engine that simulates the SMA-crossover
strategy on SPY daily data and produces a verified trade log (buy/sell
dates and prices), along with metrics and a buy-and-hold comparison —
currently only exposed as a raw API response.

This milestone is the first step of a product-structure clarification:
the chart view and the backtesting engine are becoming two separate
surfaces that both draw from the same underlying strategy logic. This
milestone handles the chart-side surface only: overlaying buy/sell signal
markers from the SMA-crossover strategy onto the existing candlestick
chart. It does NOT build the separate backtest tab/page — that's the
next milestone, and it does NOT touch cost modeling — that comes after.

## Goal
The existing chart (candlesticks + SMA overlay + RSI panel) gains buy/sell
markers at the dates the SMA-crossover strategy would have traded,
reusing the exact signal logic already verified in Milestone 9. This is a
visual, in-context addition to the chart — not a new analysis surface.

## Explicitly out of scope for this milestone
- The dedicated backtest tab/page (trade log, equity curve, full metrics
  display) — that is the next milestone, entirely separate from this one
- Transaction cost modeling — still deferred
- Any strategy other than SMA crossover
- Any ticker other than SPY, or any timeframe other than daily — matches
  Milestone 9's scope exactly; don't expand strategy coverage in this
  milestone, only add a visual layer for what already exists
- Interactivity beyond simple markers (e.g. no click-to-see-trade-detail
  popups, no marker filtering/toggling UI) — plain visual markers only
- Persisting signals to SQLite — compute on request, same as Milestone 9

Do not add any of the above even if it seems easy or natural — this
milestone is done when correct buy/sell markers appear on the SPY chart
at the right dates, nothing more.

## Design decisions (already made — don't re-litigate these)
- **Reuse, don't reimplement**: the signal dates come directly from the
  same simulation function built in Milestone 9 — do not write new
  signal-detection logic. If Milestone 9's function currently only
  returns a full backtest result (trade log + metrics + equity series),
  extract just the buy/sell dates from that existing trade log rather
  than recomputing them separately.
- **API shape**: add a lightweight endpoint focused on signals only,
  e.g. `GET /signals/sma-crossover?ticker=SPY`, returning just the list
  of signal events (date, type: buy/sell, price) — deliberately smaller
  than the full Milestone 9 backtest response, since the chart only
  needs marker placement, not the full metrics payload. This endpoint
  will likely be reused by the future backtest tab too, so keep it
  general enough to serve both, but don't build that tab's needs into it
  yet beyond what's naturally already there (date, type, price).
- **Rendering**: use lightweight-charts' built-in marker support on the
  candlestick series (e.g. up-arrow/green for buy, down-arrow/red for
  sell, or similar clear visual distinction) — check the library's
  current marker API during implementation rather than assuming a
  specific method name.
- **Where markers apply**: only on the daily SPY chart, since that's the
  only ticker/timeframe the strategy currently supports. If the user
  switches to a different ticker or timeframe (from Milestone 3/8 work),
  markers should simply not appear rather than showing incorrect or
  stale signals — don't try to generalize signal support to other
  tickers/timeframes in this milestone.

## Steps

1. **Extract signal-only data** (backend)
   - From the existing Milestone 9 simulation output, isolate just the
     buy/sell events (date, type, execution price) without the full
     metrics/equity payload.

2. **Signals endpoint**
   - `GET /signals/sma-crossover?ticker=SPY` returns the signal list as
     structured JSON. If called for anything other than SPY, return a
     clear "not supported yet" response rather than an error that looks
     like a bug (matches Milestone 9's ticker restriction).

3. **Frontend marker rendering**
   - When the chart is showing SPY on the daily timeframe, fetch signals
     from the new endpoint and render them as markers on the
     candlestick series at the correct dates.
   - When the chart is showing any other ticker or timeframe, don't
     fetch or show markers — no broken requests, no leftover markers
     from a previous view.
   - Markers should visually distinguish buy vs. sell clearly (e.g.
     color and/or shape) without needing a legend to interpret at a
     glance.

4. **Verify end to end**
   - Confirm the markers on the chart line up exactly with the buy/sell
     dates already hand-verified in Milestone 9 — this should be a
     direct visual confirmation of numbers you've already checked, not
     new verification work.
   - Confirm switching to AAPL or QQQ (or a non-daily timeframe) removes
     the markers cleanly, with no errors and no stale/incorrect markers
     left over from SPY.
   - Confirm switching back to SPY daily restores the markers correctly.

## Definition of done
The SPY daily chart shows correctly-placed, visually clear buy/sell
markers matching the SMA-crossover signals already verified in Milestone
9. Other tickers/timeframes show no markers, without errors. The
underlying signal logic is reused from Milestone 9, not reimplemented.
The dedicated backtest results tab and cost modeling remain separate,
deferred milestones.

# Milestone 11 Spec: Backtest Results Tab

## Context
Milestone 9 built the backtesting engine (SMA-crossover on SPY daily
data) with a verified trade log, metrics, and buy-and-hold comparison,
currently only reachable as a raw API response. Milestone 10 added
buy/sell markers to the chart view as a lightweight visual layer. This
milestone builds the second, separate surface described in the product
vision: a dedicated backtest results page, independent from the chart
view, showing the full analytical detail — trade log, equity curve, and
metrics. The chart page and this page are two different consumers of the
same underlying engine; neither should depend on the other's UI.

## Goal
A new page/tab, separate from the chart view, that displays the full
Milestone 9 backtest results for the SMA-crossover strategy on SPY: an
equity curve, the trade log, and summary metrics (including the
buy-and-hold comparison) — pulled from the existing backtest endpoint,
not recomputed.

## Explicitly out of scope for this milestone
- Transaction cost modeling — still deferred to after this milestone
- Any strategy other than SMA crossover
- Any ticker other than SPY
- A strategy picker, configuration UI, or the ability to run a backtest
  with different parameters from this page — this milestone displays the
  existing fixed backtest, it doesn't add configurability
- Persisting backtest runs/history to SQLite — this page calls the
  existing endpoint fresh each time it's viewed, same as Milestone 9's
  behavior; no "past runs" list
- Any change to the chart page or Milestone 10's signal markers — this
  milestone is additive, a new page, not a modification to the existing
  chart view
- Advanced charting interactivity on the equity curve (zoom, tooltips
  beyond basic hover if trivial) — a plain, readable line chart is
  sufficient

Do not add any of the above even if it seems easy or natural — this
milestone is done when the backtest results are viewable on their own
dedicated page with correct data, nothing more.

## Design decisions (already made — don't re-litigate these)
- **Separate page/route**: this is a distinct page (e.g. `/backtest` if
  using client-side routing, or a separate simple nav tab depending on
  how the frontend is currently structured) — not a panel bolted onto
  the existing chart page. Add simple navigation (e.g. two links/tabs:
  "Chart" and "Backtest") so the user can move between them.
  **No shared state required between the two pages** — the backtest
  page doesn't need to know which ticker/timeframe is currently selected
  on the chart page, since the backtest is currently fixed to SPY daily
  regardless of chart state.
- **Data source**: this page calls the existing Milestone 9
  `GET /backtest/sma-crossover?ticker=SPY` endpoint directly — no new
  backend logic needed for this milestone, this is purely a frontend
  presentation milestone.
- **Equity curve rendering**: use lightweight-charts (already a
  dependency) for consistency with the rest of the app, rendered as a
  simple line series from the equity series already returned by the
  Milestone 9 endpoint.
- **Trade log display**: a plain table is sufficient — columns for
  entry date/price, exit date/price, and per-trade return. No sorting/
  filtering UI required, though trivial default sorting (chronological)
  is expected.
- **Metrics display**: show total return, max drawdown, number of
  trades, and win rate for the strategy, alongside the same figures for
  buy-and-hold, positioned so they're easy to compare side by side (not
  buried in separate sections).

## Steps

1. **Add navigation between the two pages**
   - Simple nav (tabs or links) so the user can switch between the
     existing chart view and the new backtest page.

2. **Backtest page: fetch and display metrics**
   - Call the existing backtest endpoint on page load.
   - Display strategy metrics and buy-and-hold metrics clearly
     side-by-side (total return, max drawdown, trade count, win rate).

3. **Backtest page: equity curve**
   - Render the equity series from the endpoint response as a line chart
     using lightweight-charts.

4. **Backtest page: trade log table**
   - Render the trade log as a table (entry date/price, exit date/price,
     per-trade return), chronologically ordered.

5. **Verify end to end**
   - Confirm the metrics shown on this page match exactly what Milestone
     9's endpoint returns and what was hand-verified there — no
     transformation or recalculation should change the numbers.
   - Confirm the equity curve visually matches the trade log (e.g.
     portfolio value should step up/down at the trade dates shown in the
     table, not drift inconsistently).
   - Confirm navigating between the chart page and this page works
     cleanly in both directions, and that neither page's state affects
     the other (e.g. switching tickers on the chart page doesn't change
     anything on the backtest page, since it's still fixed to SPY).

## Definition of done
A separate backtest page is reachable via simple navigation from the
chart view, displaying the SMA-crossover strategy's equity curve, full
trade log, and metrics (with buy-and-hold comparison) for SPY — all
pulled directly from the existing Milestone 9 endpoint with no numbers
changed in transit. The chart page and Milestone 10's markers are
unaffected. Cost modeling, other strategies, other tickers, and any
backtest-configuration UI remain deferred to future milestones.

# Milestone 12 Spec: Transaction Cost Modeling

## Context
Milestone 9 built the SMA-crossover backtesting engine on an explicitly
frictionless assumption (no fees, no slippage) — a known, intentional
simplification flagged at the time. Milestone 11 gave backtest results a
dedicated page, separate from the chart view. This milestone closes the
frictionless gap: the engine now also computes cost-adjusted results, and
the backtest page shows both side by side so the actual cost sensitivity
of the strategy is visible, not hidden behind a single optimistic number.

## Goal
The existing SMA-crossover simulation produces both a frictionless result
(as before) and a cost-adjusted result (with a simple per-trade
commission applied), and the backtest page displays both together so the
user can see exactly how much of the strategy's apparent performance
depends on ignoring trading costs.

## Explicitly out of scope for this milestone
- Slippage modeling (price impact / worse-than-close fills) — deferred;
  this milestone covers commission-style costs only, since slippage is
  harder to estimate honestly without real fill data
- Any strategy other than SMA crossover
- Any ticker other than SPY
- A UI to configure the cost rate — the cost rate is a backend parameter
  with a sensible default, not yet exposed for the user to change (same
  "parameterize now, expose later" pattern used for indicator settings
  before Milestone 5 existed)
- Any change to Milestone 10's chart markers — signals themselves don't
  change, only the performance numbers derived from them
- Persisting backtest results to SQLite — still computed fresh per
  request, as in Milestone 9

Do not add any of the above even if it seems easy or natural — this
milestone is done when frictionless and cost-adjusted results are both
correctly computed and both visible on the backtest page.

## Design decisions (already made — don't re-litigate these)
- **Cost model**: a flat percentage commission (default 0.1%) applied to
  the trade value on both entry and exit. No fixed-dollar fee, no
  slippage — the simplest honest approximation, not a precise model of
  any specific broker.
- **Implementation as a parameter**: the cost rate should be a parameter
  to the simulation function (e.g. `cost_pct=0.001`), not a hardcoded
  constant — even though there's no UI to change it yet, this keeps the
  door open for later configurability without a rewrite.
- **Both results computed together**: the same simulation logic and
  trade log/signal dates are reused for both frictionless and
  cost-adjusted runs — the only difference is whether the cost is
  deducted at each trade. Don't duplicate the simulation logic; run it
  with cost_pct=0 for the frictionless case and cost_pct=0.001 (default)
  for the cost-adjusted case, or an equivalent single-pass approach if
  cleaner.
- **API shape**: extend the existing `GET /backtest/sma-crossover`
  response to include both result sets (e.g. a `frictionless` and a
  `cost_adjusted` object, each with its own metrics, trade log, and
  equity series) rather than requiring two separate calls.
- **Display**: the backtest page (Milestone 11) shows both results
  side by side (e.g. two columns, or a toggle between them) — pick
  whichever is simpler to implement clearly. Side-by-side is preferred
  if straightforward, since direct comparison is the point of this
  milestone.

## Steps

1. **Extend the simulation function** (backend)
   - Add a `cost_pct` parameter to the existing Milestone 9 simulation
     function. When non-zero, deduct `cost_pct * trade value` from the
     portfolio at both the entry and exit of each trade.
   - Confirm the function still produces the exact same output as
     Milestone 9 when `cost_pct=0` — this is a correctness check that
     the change is additive, not a rewrite of existing verified logic.

2. **Run both variants and extend the API response**
   - Call the simulation twice (or via one pass computing both, if
     cleaner): once frictionless (`cost_pct=0`), once cost-adjusted
     (`cost_pct=0.001` default).
   - Update `GET /backtest/sma-crossover?ticker=SPY` to return both
     result sets in the response, each with its own metrics, trade log,
     and equity series. Buy-and-hold comparison stays as a single
     result (it isn't affected by a trading cost model, since it
     involves only one trade).

3. **Update the backtest page** (frontend)
   - Display both the frictionless and cost-adjusted equity curves,
     metrics, and trade logs, positioned so they're easy to compare
     directly (side-by-side columns, or a clearly labeled toggle).
   - Make it visually obvious which numbers are which — don't just show
     two unlabeled tables.

4. **Verify end to end**
   - Confirm the frictionless results are byte-for-byte identical to
     what Milestone 9/11 already showed and verified — nothing should
     have silently changed for the cost_pct=0 case.
   - Hand-check one specific trade's cost-adjusted net return: take its
     entry/exit prices, apply the 0.1% cost at both ends manually, and
     confirm it matches what the cost-adjusted trade log reports.
   - Confirm the cost-adjusted total return is lower than the
     frictionless total return by an amount consistent with the number
     of trades (more trades → more cumulative cost drag) — sanity-check
     this relationship makes sense given the trade count from the
     existing verified trade log.
   - Confirm the buy-and-hold comparison figure is unchanged and
     identical between the two displayed result sets, since it isn't
     affected by the cost model.

## Definition of done
The backtest page shows both frictionless and cost-adjusted results for
the SMA-crossover strategy on SPY, clearly labeled and easy to compare.
The cost-adjusted numbers are verified correct by hand against a
manually recomputed trade. Frictionless results are unchanged from
Milestones 9 and 11. Slippage modeling, cost configurability UI, other
strategies, and other tickers remain deferred to future milestones.

# Milestone 13 Spec: Intraday Data Accumulation

## Context
Milestone 8 added timeframe selection (1 day / 1 hour / 5 minute), with
intraday data fetched **on-demand only** — pulled when a user requests
that timeframe, not on any schedule. This means intraday history is
bounded by whatever yfinance's own retention window currently holds (60
days for 1h/5m), and nothing is done to preserve data before it ages out
of that window.

This milestone changes that: intraday timeframes are now included in the
existing scheduled fetch (Milestone 6) and startup staleness check
(Milestone 7), so bars are pulled regularly and accumulated in SQLite
over time — building a longer history than any single yfinance query
could ever return, since old rows are preserved even after yfinance's own
window slides past them.

## Important constraint — read before implementing
This is accumulation, not backfill. Historical intraday bars that have
already aged out of yfinance's retention window **cannot be recovered** —
there is no way to fetch 5-minute bars from 4 months ago if yfinance no
longer has them. This milestone only ensures that, going forward, nothing
new gets lost. If the backend hasn't run in longer than a timeframe's
retention window (e.g. hasn't run in 70+ days, longer than 5m's 60-day
window), there will be a permanent, unrecoverable gap for that period —
that's an accepted limitation, not a bug to fix. Handle it by logging
clearly, not by erroring or crashing.

## Goal
The existing scheduled job and startup catch-up now also fetch and
upsert 1-hour and 5-minute bars (in addition to the existing daily
fetch) for all watchlist tickers, using the same fetch/cache logic
already built in Milestone 8 — with the critical guarantee that
previously-accumulated rows are never deleted or overwritten by a
fetch that no longer includes them in its returned window.

## Explicitly out of scope for this milestone
- 1-minute timeframe — still deferred, same as Milestone 8's original
  scope; its 7-day window makes accumulation valuable but this milestone
  proves the mechanism on the wider 1h/5m windows first
- Any change to fetch cadence beyond the existing daily schedule — don't
  add sub-daily/hourly scheduling triggers; once-daily is enough to keep
  intraday accumulation gap-free given the 60-day retention windows
  involved (a daily fetch overlaps the prior window by a wide margin)
- New data fields (dividends, splits, fundamentals) — separate milestone
- TA-Lib or any new indicator library — separate milestone
- Any new tickers beyond the existing watchlist
- A UI to show accumulated history depth/growth — backend and logging
  only for this milestone; a "how much history do I have" view can come
  later if useful

Do not add any of the above even if it seems easy or natural.

## Design decisions (already made — don't re-litigate these)
- **Additive fetch, never destructive**: the fetch/upsert logic must add
  new rows and update genuinely changed ones (e.g. a very recent bar that
  was previously partial), but must never delete or bulk-replace existing
  cached rows for a ticker+timeframe just because the latest yfinance
  response no longer includes them. This is the entire mechanism accumulation
  depends on — verify explicitly that Milestone 8's existing fetch
  function behaves this way, and fix it if it currently does a
  replace-all rather than a true upsert.
- **Same cadence as the existing daily job**: intraday fetches piggyback
  on the Milestone 6 scheduled run and Milestone 7 startup check, rather
  than introducing a separate schedule. Simpler to reason about, and
  sufficient given the retention windows involved.
- **Reuse Milestone 8's fetch logic**: no new fetch code — the scheduler
  and startup check now call the existing per-timeframe fetch function
  for 1h and 5m in addition to 1d, for every ticker in the watchlist.
- **Staleness check extended, not replaced**: Milestone 7's staleness
  check gets extended to also check 1h/5m freshness per ticker, using a
  reasonable freshness threshold for each (e.g. 5m data stale if older
  than a few hours, vs. 1d's "last completed trading day" threshold) —
  not held to the same staleness definition as daily data.

## Steps

1. **Verify/fix upsert behavior** (backend)
   - Audit Milestone 8's existing intraday fetch-and-cache function.
     Confirm it upserts (insert new rows, update existing ones by
     matching key) rather than deleting/replacing all rows for that
     ticker+timeframe on each fetch. Fix this first if it doesn't already
     work this way — everything else in this milestone depends on it.

2. **Extend the scheduled job**
   - Update the Milestone 6 scheduled job to loop over 1h and 5m (in
     addition to the existing 1d fetch) for every watchlist ticker,
     upserting into the same schema from Milestone 8.
   - Wrap each ticker/timeframe combination in the same per-item error
     handling from Milestone 6, so one failure doesn't block the rest.

3. **Extend the startup staleness check**
   - Update Milestone 7's check to also evaluate 1h/5m freshness per
     ticker, using a sensible freshness threshold per timeframe (not the
     daily "last trading day" logic — intraday data goes stale faster).
   - Trigger a catch-up fetch for any stale ticker/timeframe combination
     on startup, same non-blocking behavior as Milestone 7.

4. **Verify end to end**
   - Run the scheduled/startup fetch and confirm 1h and 5m rows are
     inserted for all tickers, with no duplicates on repeated runs.
   - Confirm previously-cached intraday rows are still present and
     unchanged after a fetch whose current yfinance response window no
     longer includes them (e.g. check row count and oldest cached
     timestamp before and after a fetch — the oldest row should not
     disappear or shift forward).
   - Simulate a startup after a gap (e.g. temporarily adjust the last-
     fetched timestamp in the database, or just observe behavior after a
     real gap) and confirm the catch-up fetch pulls what's still
     available within the retention window, and logs clearly (without
     erroring) if part of the gap is unrecoverable.
   - Confirm existing 1-day behavior, the chart, indicators, and
     backtest features are all unaffected by this change.

## Definition of done
The scheduled job and startup check now accumulate 1-hour and 5-minute
history for all watchlist tickers over time, in addition to daily data,
using upsert logic verified to never destroy previously-accumulated
rows. Running the backend regularly over weeks/months results in
intraday history deeper than yfinance's own retention window would
provide on a single fresh query. 1-minute timeframe, new data fields,
and TA-Lib integration remain separate, deferred milestones.

# Milestone 14 Spec: Dividends, Splits, and Fundamentals Data

## Context
Milestones 1-13 are complete: multi-ticker dashboard with configurable
indicators, a scheduled + startup-checked fetch pipeline that now
accumulates intraday history (Milestone 13), and a backtesting engine
with cost modeling. This milestone expands what data is stored beyond
OHLCV price bars — adding dividends, stock splits, and a small set of
basic fundamentals (market cap, sector, industry, P/E ratio) for each
watchlist ticker. This is a data-layer milestone only: fetch and store,
don't yet wire this data into charts, indicators, or the backtester.

## Goal
For each ticker in the watchlist, fetch and persist dividend history,
split history, and a small snapshot of basic fundamentals from yfinance,
refreshed on a sensible (much less frequent than price data) cadence,
and exposed via simple read endpoints.

## Explicitly out of scope for this milestone
- Displaying dividends/splits/fundamentals anywhere in the frontend
  (chart markers for dividends, a fundamentals panel, etc.) — this
  milestone is fetch-and-store plus a raw API, not UI
- Adjusting historical OHLCV prices for splits/dividends, or changing
  any existing price-fetch behavior — this milestone adds new, separate
  data alongside existing price data, it does not modify how prices are
  fetched or stored
- Using this data in the backtester (e.g. accounting for dividends in
  returns) — a real future improvement, but separate from just having
  the data available
- A large or exhaustive fundamentals field set — deliberately limited to
  a small, useful starting set (see below); more fields can be added
  later once these are proven working
- Historical fundamentals as a time series — fundamentals are stored as
  a single current snapshot per ticker, not tracked over time, for this
  milestone

Do not add any of the above even if it seems easy or natural — this
milestone is done when dividends, splits, and basic fundamentals are
correctly fetched, stored, and retrievable via API for every watchlist
ticker.

## Important note on fundamentals fetching
yfinance's fundamentals data (via `Ticker.info`) is less reliable than
its price-history data — it can be slower, occasionally incomplete for a
given symbol, or shift in structure between yfinance versions. Treat
fundamentals fetch failures as expected/recoverable (log and skip,
don't crash), same general posture as the per-ticker error handling
already used for price fetches since Milestone 6.

## Design decisions (already made — don't re-litigate these)
- **Fundamentals field set for this milestone**: market cap, sector,
  industry, and trailing P/E ratio. Deliberately small — this is a
  starting set, not the full breadth available from yfinance.
- **New tables**: `dividends` (ticker_id, date, amount), `splits`
  (ticker_id, date, ratio), and `fundamentals` (ticker_id, market_cap,
  sector, industry, pe_ratio, last_updated) — fundamentals as a single
  row per ticker (upserted/overwritten on refresh), not a history table.
- **Fetch cadence**: much less frequent than price data, since these
  change slowly. Dividends/splits: refresh on the existing daily
  schedule (Milestone 6) — cheap to check in full each time since the
  datasets are small, upsert as usual. Fundamentals: refresh only if the
  stored snapshot is older than a longer threshold (e.g. 7 days), not on
  every daily run, to reduce reliance on the less-stable `Ticker.info`
  call.
- **Reuse existing scheduling infrastructure**: piggyback on Milestone
  6's scheduled job and Milestone 7's per-ticker error handling pattern,
  rather than building a separate scheduling mechanism for this new
  data.
- **API shape**: simple read endpoints — `GET /dividends/{ticker}`,
  `GET /splits/{ticker}`, `GET /fundamentals/{ticker}` — each returning
  the stored data for that ticker as-is, no computation or joining with
  price data yet.

## Steps

1. **New tables** (backend)
   - Create `dividends`, `splits`, and `fundamentals` tables per the
     schema above.

2. **Fetch functions**
   - Dividend/split fetch: pull full history via yfinance for a given
     ticker, upsert into the respective tables (same upsert discipline
     used for price data — don't duplicate rows on re-run).
   - Fundamentals fetch: pull the four fields listed above via
     `Ticker.info` (or equivalent), upsert the single snapshot row per
     ticker. Wrap in error handling so a failure for one ticker (or a
     missing field for a given symbol) doesn't stop others from
     updating.

3. **Wire into the scheduler**
   - Extend the Milestone 6 scheduled job (and Milestone 7 startup
     check, if it makes sense there too) to also run dividend/split
     fetches every run, and fundamentals fetches only when the stored
     snapshot is older than the configured threshold (default 7 days).

4. **API endpoints**
   - Add the three read endpoints listed above, returning stored data
     for a given ticker as structured JSON. Return a clear empty/not-
     found response if no data exists yet for a ticker rather than an
     error.

5. **Verify end to end**
   - Run the fetch for all three watchlist tickers; confirm dividend and
     split history lands correctly — spot-check SPY's dividend history
     against a known public source to confirm dates/amounts are
     sensible.
   - Confirm fundamentals snapshot is populated with plausible values
     (e.g. SPY's sector/industry classification, a reasonable market cap
     figure) for each ticker.
   - Re-run the fetch and confirm no duplicate rows are created in
     `dividends`/`splits`, and that `fundamentals` correctly updates
     (not duplicates) the single row per ticker.
   - Confirm fundamentals do NOT re-fetch on every single scheduled run
     — only when the snapshot exceeds the staleness threshold. Verify by
     checking `last_updated` doesn't change on a run that happens before
     the threshold is reached.
   - Confirm a simulated fundamentals fetch failure (e.g. temporarily use
     an invalid ticker) doesn't block dividend/split fetching or other
     tickers' fundamentals from updating.

## Definition of done
Dividend history, split history, and a basic fundamentals snapshot
(market cap, sector, industry, P/E) are correctly fetched and stored for
every watchlist ticker, retrievable via three simple read endpoints.
Dividends/splits refresh on the existing daily schedule; fundamentals
refresh on a longer cadence to reduce reliance on a less stable data
source. No UI, backtester integration, or price-adjustment changes were
made — this data exists and is retrievable, nothing more.

# Milestone 15 Spec: TA-Lib Integration (MACD)

## Context
Milestones 1-14 are complete: multi-ticker dashboard with hand-implemented
SMA and RSI (verified by hand in Milestones 2 and 4), a configuration
layer for those two indicators, multi-timeframe support with intraday
accumulation, dividends/splits/fundamentals data, and a backtesting
engine with cost modeling. This milestone introduces TA-Lib as a
dependency and uses it to add one new indicator — MACD — rather than
reimplementing it by hand as SMA/RSI were.

## Goal
Add MACD (Moving Average Convergence Divergence) as a third indicator,
computed via TA-Lib, rendered in its own chart panel, following the same
overall pattern established by RSI (Milestone 4) — but using a library
function instead of custom calculation code.

## Explicitly out of scope for this milestone
- Reimplementing or replacing the existing SMA/RSI calculations with
  TA-Lib equivalents — those remain as-is, hand-verified, and untouched.
  This milestone only adds MACD as something new.
- Any other TA-Lib indicator beyond MACD (Bollinger Bands, stochastic,
  ATR, etc.) — one new indicator, to prove out the TA-Lib integration
  itself, before adding more
- Adding MACD to the Milestone 5 configuration UI/settings table —
  MACD's parameters are function/API parameters with sensible defaults,
  same as RSI was before Milestone 5 existed, not yet user-configurable
  through the settings panel
- Using MACD in the backtester or as a new strategy — this milestone is
  chart display only, same scope boundary RSI had in Milestone 4
- Any change to fetch scheduling, data accumulation, or fundamentals
  work from Milestones 12-14

Do not add any of the above even if it seems easy or natural — this
milestone is done when MACD renders correctly, computed via TA-Lib,
verified against a reliable reference.

## Design decisions (already made — don't re-litigate these)
- **Dependency**: add `TA-Lib` (the Python wrapper) to the project's
  dependencies. As of recent versions it ships prebuilt wheels for
  common platforms/Python versions, so installation should be
  straightforward via pip — but confirm this works cleanly in this
  project's actual environment before proceeding, and flag it clearly if
  it doesn't (e.g. falls back to needing a system-level library install).
- **Default parameters**: standard MACD settings — 12-period fast EMA,
  26-period slow EMA, 9-period signal line — implemented as parameters,
  not hardcoded, following the same pattern used for SMA's window and
  RSI's window/thresholds.
- **API shape**: extend the existing `GET /prices/{ticker}` endpoint
  further, e.g. `?macd=1` (or with explicit `macd_fast`/`macd_slow`/
  `macd_signal` overrides), independent of the existing `sma`/`rsi`
  params — all three should be usable together or independently.
- **Rendering**: MACD gets its own panel, separate from price and from
  the RSI panel, since it has its own distinct scale — same
  multi-pane approach used for RSI in Milestone 4. A standard MACD
  display includes the MACD line, the signal line, and a histogram
  (the difference between them) — implement all three, since that's
  what makes MACD readable, not just the MACD line alone.
- **Verification approach**: MACD is harder to hand-calculate step by
  step than SMA or RSI (it involves two EMAs plus a signal line EMA on
  top). Rather than manually recomputing it from scratch, cross-check
  TA-Lib's output for a few dates against a second reliable source (e.g.
  a well-known charting site's MACD values for the same ticker/dates, or
  TA-Lib's own documented test vectors if available) to confirm the
  values are sane and correctly aligned to the right dates — full manual
  recomputation isn't required here the way it was for SMA/RSI.

## Steps

1. **Add and verify the TA-Lib dependency**
   - Install TA-Lib in the project environment. Confirm it imports and a
     basic function call works before writing any integration code.
     Note in your response how installation went (clean via wheel, or
     required extra steps) — this affects whether TA-Lib is a
     comfortable long-term dependency for a solo-maintained project.

2. **MACD calculation** (backend)
   - A function that takes a series of closes and the three period
     parameters (fast/slow/signal), returns MACD line, signal line, and
     histogram series using TA-Lib's MACD function.

3. **Extend the API endpoint**
   - `GET /prices/{ticker}?macd=1` (with optional period overrides)
     returns MACD line/signal/histogram alongside existing OHLCV/SMA/RSI
     data, independently of those other params.

4. **Frontend MACD panel**
   - Add a third chart pane (below price and RSI) rendering the MACD
     line, signal line, and histogram, time-synchronized with the other
     panes.
   - Panel updates correctly when the ticker or timeframe selection
     changes, consistent with how SMA/RSI already behave.

5. **Verify end to end**
   - Cross-check MACD values for a few dates against a second source,
     per the verification approach above, confirming values and dates
     align correctly.
   - Confirm the MACD panel is time-synchronized with the price and RSI
     panels above it.
   - Confirm requesting `?macd=1` works independently of `?sma=`/`?rsi=`
     — all three indicators remain independently toggleable via query
     params, none breaks the others.
   - Confirm switching tickers/timeframes updates the MACD panel
     correctly alongside the existing panels.

## Definition of done
Selecting any watchlist ticker shows the existing candlestick+SMA chart
and RSI panel, plus a new MACD panel (line, signal, histogram) computed
via TA-Lib, cross-checked against a reliable reference. TA-Lib is
confirmed to install cleanly in this project's environment. SMA and RSI
remain hand-implemented and unchanged. MACD configuration UI and
backtester integration remain deferred to future milestones.

# Milestone 16 Spec: Extend Configuration Layer to MACD

## Context
Milestones 1-15 are complete, including the Milestone 5 configuration
layer (currently covering SMA's window/color and RSI's window/thresholds/
color, persisted in SQLite) and Milestone 15's addition of MACD via
TA-Lib (currently using hardcoded-but-parameterized defaults: 12/26/9
periods, no stored settings, no UI). This milestone closes that gap by
extending the existing configuration layer to also cover MACD, so all
three indicators are configurable through the same mechanism rather than
two out of three.

## Goal
MACD's parameters (fast period, slow period, signal period) and line
colors (MACD line, signal line) become configurable through the existing
settings table and UI, persisted the same way SMA and RSI already are.

## Explicitly out of scope for this milestone
- Any new indicator — this milestone only extends configuration coverage
  to MACD, it doesn't add Bollinger Bands or anything else
- Per-ticker configuration — settings remain global, consistent with the
  Milestone 5 scope decision
- Histogram-specific color configuration — keep this pass to MACD line
  and signal line colors only, matching the "one new surface, not
  maximal scope" discipline used elsewhere; histogram color can be added
  later if wanted
- Saved presets or multiple configurations — still one active global
  config, same as Milestone 5
- Any change to SMA or RSI's existing configuration — this milestone is
  purely additive for MACD, don't touch their stored settings, API
  handling, or UI

Do not add any of the above even if it seems easy or natural — this
milestone is done when MACD's parameters and colors are configurable,
persisted, and validated the same way SMA/RSI's already are.

## Design decisions (already made — don't re-litigate these)
- **Extend, don't replace**: add new columns to the existing
  `indicator_settings` table (e.g. `macd_fast`, `macd_slow`,
  `macd_signal`, `macd_line_color`, `macd_signal_color`) rather than
  creating a separate table — keeps all indicator settings in one place,
  consistent with how SMA and RSI are already stored.
- **Defaults on first run**: if the settings row predates this milestone
  (i.e. was created before MACD columns existed) or no row exists yet,
  fall back to MACD's current hardcoded defaults (12/26/9, reasonable
  default colors) — don't error, don't lose existing SMA/RSI settings
  already stored in that row.
- **Validation**: fast period < slow period is a real constraint worth
  enforcing server-side (a MACD with fast >= slow is not meaningful) —
  same validation discipline already used for RSI's oversold < overbought
  check in Milestone 5.
- **API**: extend the existing `GET /settings` / `PUT /settings`
  endpoints to include the new MACD fields alongside the existing SMA/RSI
  fields — one settings object, not a separate endpoint for MACD.
- **Wiring**: the existing MACD calculation/endpoint (Milestone 15) reads
  its fast/slow/signal periods from stored settings instead of hardcoded
  constants, same pattern already used for SMA's window and RSI's
  window/thresholds.

## Steps

1. **Extend the settings table** (backend)
   - Add `macd_fast`, `macd_slow`, `macd_signal`, `macd_line_color`,
     `macd_signal_color` columns to `indicator_settings`.
   - Handle the migration/default-seeding case so existing rows (created
     before this milestone) gain sensible MACD defaults rather than
     breaking or returning nulls.

2. **Extend settings API validation and handling**
   - Update `GET /settings` to include the new MACD fields.
   - Update `PUT /settings` to accept and validate them — periods > 0,
     fast < slow — rejecting invalid combinations with a clear error,
     consistent with existing RSI validation.

3. **Wire MACD calculation to stored settings**
   - Update the Milestone 15 MACD endpoint/calculation to pull
     fast/slow/signal periods from `indicator_settings` rather than
     hardcoded defaults, mirroring exactly how SMA/RSI already do this.

4. **Extend the settings UI**
   - Add MACD's fields (three period number inputs, two color pickers) to
     the existing settings panel alongside SMA and RSI's controls.
   - Saving updates the chart's MACD panel without a page reload, same
     behavior as the existing SMA/RSI settings.

5. **Verify end to end**
   - Change MACD's periods and colors via the settings UI; confirm the
     MACD panel updates to reflect both.
   - Restart the backend and reload the frontend; confirm MACD settings
     persisted, alongside confirming SMA/RSI settings are still intact
     and unaffected.
   - Submit an invalid MACD combination (e.g. fast >= slow) and confirm
     it's rejected with a clear error, not silently accepted.
   - Confirm settings apply consistently across all watchlist tickers,
     same as SMA/RSI (global, not per-ticker).

## Definition of done
MACD's fast/slow/signal periods and line/signal colors are configurable
through the same settings panel and API used for SMA and RSI, persisted
in the same `indicator_settings` table, validated with the same rigor
(fast < slow enforced), and unaffected by restarts. SMA and RSI's
existing configuration is untouched. All three indicators are now
configurable through one consistent mechanism — no indicator is left on
hardcoded defaults with no way to change them through the UI.