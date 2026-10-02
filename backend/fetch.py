"""Fetch OHLCV data, dividends, splits, and fundamentals for tickers."""

import logging
import time
from datetime import datetime, timezone

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

    # Drop rows where any OHLCV field is NaN (partial/missing data from yfinance).
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

    if df.empty:
        logger.warning("All rows had NaN values for %s (%s) — skipping", symbol, timeframe)
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


def fetch_dividends(conn, ticker_id: int, symbol: str) -> int:
    """Fetch and upsert dividend history for a single ticker. Returns row count."""
    ticker = yf.Ticker(symbol)
    divs = ticker.dividends

    if divs.empty:
        return 0

    rows = []
    for dt, amount in divs.items():
        rows.append((ticker_id, dt.strftime("%Y-%m-%d"), round(float(amount), 6)))

    conn.executemany(
        """
        INSERT INTO dividends (ticker_id, date, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(ticker_id, date) DO UPDATE SET amount = excluded.amount
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_splits(conn, ticker_id: int, symbol: str) -> int:
    """Fetch and upsert split history for a single ticker. Returns row count."""
    ticker = yf.Ticker(symbol)
    splits = ticker.splits

    if splits.empty:
        return 0

    rows = []
    for dt, ratio in splits.items():
        rows.append((ticker_id, dt.strftime("%Y-%m-%d"), round(float(ratio), 6)))

    conn.executemany(
        """
        INSERT INTO splits (ticker_id, date, ratio)
        VALUES (?, ?, ?)
        ON CONFLICT(ticker_id, date) DO UPDATE SET ratio = excluded.ratio
        """,
        rows,
    )
    conn.commit()
    return len(rows)


FUNDAMENTALS_STALE_DAYS = 7


def fetch_fundamentals(conn, ticker_id: int, symbol: str) -> bool:
    """Fetch and upsert fundamentals snapshot if stale (> 7 days old).

    Returns True if an update was performed, False if skipped.
    """
    row = conn.execute(
        "SELECT last_updated FROM fundamentals WHERE ticker_id = ?",
        (ticker_id,),
    ).fetchone()

    if row is not None:
        try:
            last = datetime.strptime(row["last_updated"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            age_days = (datetime.now(timezone.utc) - last).total_seconds() / 86400
            if age_days < FUNDAMENTALS_STALE_DAYS:
                return False
        except ValueError:
            pass  # can't parse — treat as stale, re-fetch

    ticker = yf.Ticker(symbol)
    info = ticker.info

    market_cap = info.get("marketCap")
    sector = info.get("sector")
    industry = info.get("industry")
    pe_ratio = info.get("trailingPE")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        """
        INSERT INTO fundamentals (ticker_id, market_cap, sector, industry, pe_ratio, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker_id) DO UPDATE SET
            market_cap   = excluded.market_cap,
            sector       = excluded.sector,
            industry     = excluded.industry,
            pe_ratio     = excluded.pe_ratio,
            last_updated = excluded.last_updated
        """,
        (ticker_id, market_cap, sector, industry, pe_ratio, now_str),
    )
    conn.commit()
    return True


def fetch_extras() -> None:
    """Fetch dividends, splits, and fundamentals for all tickers."""
    init_db()
    conn = get_connection()

    tickers = conn.execute("SELECT id, symbol FROM tickers ORDER BY id").fetchall()

    for ticker_row in tickers:
        ticker_id = ticker_row["id"]
        symbol = ticker_row["symbol"]

        try:
            count = fetch_dividends(conn, ticker_id, symbol)
            if count:
                logger.info("Upserted %d dividend rows for %s", count, symbol)
        except Exception:
            logger.exception("Failed to fetch dividends for %s", symbol)

        try:
            count = fetch_splits(conn, ticker_id, symbol)
            if count:
                logger.info("Upserted %d split rows for %s", count, symbol)
        except Exception:
            logger.exception("Failed to fetch splits for %s", symbol)

        try:
            updated = fetch_fundamentals(conn, ticker_id, symbol)
            if updated:
                logger.info("Updated fundamentals for %s", symbol)
            else:
                logger.info("Fundamentals for %s still fresh — skipping", symbol)
        except Exception:
            logger.exception("Failed to fetch fundamentals for %s", symbol)

    conn.close()


def fetch_all_timeframes() -> None:
    """Fetch data for all tickers across all supported timeframes (1d, 1h, 5m),
    plus dividends, splits, and fundamentals."""
    for tf in TIMEFRAME_CONFIG:
        logger.info("Fetching all tickers for timeframe %s", tf)
        fetch(tf)
    fetch_extras()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
