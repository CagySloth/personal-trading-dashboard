"""Fetch OHLCV data for tickers and upsert into SQLite."""

import logging
import time

import yfinance as yf
from database import get_connection, init_db

logger = logging.getLogger(__name__)

# In-memory cache of last-fetch unix timestamps per (ticker_id, timeframe).
_last_fetch_times: dict = {}

# How many seconds before cached intraday data is considered stale.
_STALE_SECONDS = {
    "1h": 3600,   # 1 hour
    "5m": 300,    # 5 minutes
}

# yfinance interval → (period to request, datetime format for storage)
TIMEFRAME_CONFIG = {
    "1d": ("max", "%Y-%m-%d"),
    "1h": ("730d", "%Y-%m-%d %H:%M:%S"),
    "5m": ("60d", "%Y-%m-%d %H:%M:%S"),
}


def fetch_ticker(conn, ticker_id: int, symbol: str, timeframe: str = "1d") -> int:
    """Fetch and upsert bars for a single ticker+timeframe. Returns row count."""
    config = TIMEFRAME_CONFIG.get(timeframe)
    if config is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    period, dt_fmt = config

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=timeframe)

    if df.empty:
        logger.warning("No data returned for %s (%s)", symbol, timeframe)
        return 0

    rows = []
    for dt, r in df.iterrows():
        rows.append((
            ticker_id,
            timeframe,
            dt.strftime(dt_fmt),
            round(r["Open"], 4),
            round(r["High"], 4),
            round(r["Low"], 4),
            round(r["Close"], 4),
            int(r["Volume"]),
        ))

    conn.executemany(
        """
        INSERT INTO prices (ticker_id, timeframe, datetime, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker_id, timeframe, datetime) DO UPDATE SET
            open   = excluded.open,
            high   = excluded.high,
            low    = excluded.low,
            close  = excluded.close,
            volume = excluded.volume
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def ensure_fresh(ticker_id: int, symbol: str, timeframe: str) -> None:
    """On-demand fetch-and-cache for intraday timeframes.

    Checks an in-memory TTL cache; if the data for this ticker+timeframe
    hasn't been fetched within the staleness threshold, triggers a fresh
    pull from yfinance.  Daily data is skipped here (handled by the
    scheduler / startup staleness check instead).
    """
    if timeframe == "1d":
        return  # daily data managed by scheduler / startup check

    key = (ticker_id, timeframe)
    threshold = _STALE_SECONDS.get(timeframe, 3600)
    last = _last_fetch_times.get(key, 0)

    if time.time() - last < threshold:
        return  # cache is still fresh

    conn = get_connection()
    try:
        count = fetch_ticker(conn, ticker_id, symbol, timeframe)
        _last_fetch_times[key] = time.time()
        if count:
            logger.info("On-demand fetch: %d rows for %s (%s)", count, symbol, timeframe)
    except Exception:
        logger.exception("On-demand fetch failed for %s (%s)", symbol, timeframe)
    finally:
        conn.close()


def fetch(timeframe: str = "1d") -> None:
    """Fetch data for all tickers at the given timeframe."""
    init_db()
    conn = get_connection()

    tickers = conn.execute("SELECT id, symbol FROM tickers ORDER BY id").fetchall()

    for ticker_row in tickers:
        ticker_id = ticker_row["id"]
        symbol = ticker_row["symbol"]

        try:
            count = fetch_ticker(conn, ticker_id, symbol, timeframe)
            if count:
                logger.info("Upserted %d rows for %s (%s)", count, symbol, timeframe)
        except Exception:
            logger.exception("Failed to fetch %s (%s)", symbol, timeframe)

    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
