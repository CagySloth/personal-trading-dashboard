import logging
import re
import threading
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_connection, init_db, is_data_stale, is_intraday_stale
from backtest import run_backtest, extract_signals
from fetch import fetch, fetch_all_timeframes, fetch_extras, ensure_fresh, TIMEFRAME_CONFIG
from indicators import sma, rsi, macd

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_all_timeframes, "cron", hour=16, minute=30, timezone="US/Eastern", id="daily_fetch")


def _startup_staleness_check() -> None:
    # Check daily data staleness.
    stale, latest, expected = is_data_stale()
    if stale:
        logger.info(
            "Daily data is stale (latest: %s, expected: %s) — running catch-up fetch",
            latest, expected,
        )
        fetch()
        logger.info("Daily catch-up fetch complete")
    else:
        logger.info("Daily data is current (latest: %s) — skipping fetch", latest)

    # Check intraday data staleness (1h, 5m).
    for tf in ("1h", "5m"):
        intraday_stale, intra_latest = is_intraday_stale(tf)
        if intraday_stale:
            logger.info(
                "%s data is stale (latest: %s) — running catch-up fetch", tf, intra_latest,
            )
            fetch(tf)
            logger.info("%s catch-up fetch complete", tf)
        else:
            logger.info("%s data is current (latest: %s) — skipping fetch", tf, intra_latest)

    # Fetch dividends, splits, and fundamentals (fundamentals only if stale > 7 days).
    logger.info("Checking dividends, splits, and fundamentals")
    fetch_extras()
    logger.info("Dividends/splits/fundamentals check complete")


@asynccontextmanager
async def lifespan(app):
    init_db()
    scheduler.start()
    logger.info("Scheduler started — daily fetch at 4:30 PM ET")
    threading.Thread(target=_startup_staleness_check, daemon=True).start()
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class SettingsUpdate(BaseModel):
    sma_window: Optional[int] = None
    sma_color: Optional[str] = None
    rsi_window: Optional[int] = None
    rsi_overbought: Optional[float] = None
    rsi_oversold: Optional[float] = None
    rsi_color: Optional[str] = None
    macd_fast: Optional[int] = None
    macd_slow: Optional[int] = None
    macd_signal: Optional[int] = None
    macd_line_color: Optional[str] = None
    macd_signal_color: Optional[str] = None


def _validate_settings(body: SettingsUpdate, current: dict) -> None:
    """Validate settings fields, raising HTTPException on invalid input."""
    for field in ("sma_window", "rsi_window", "macd_fast", "macd_slow", "macd_signal"):
        val = getattr(body, field)
        if val is not None and val < 1:
            raise HTTPException(status_code=422, detail=f"{field} must be >= 1")

    for field in ("sma_color", "rsi_color", "macd_line_color", "macd_signal_color"):
        val = getattr(body, field)
        if val is not None and not HEX_COLOR_RE.match(val):
            raise HTTPException(status_code=422, detail="Color must be a hex string like #RRGGBB")

    overbought = body.rsi_overbought if body.rsi_overbought is not None else current["rsi_overbought"]
    oversold = body.rsi_oversold if body.rsi_oversold is not None else current["rsi_oversold"]

    if oversold <= 0 or overbought >= 100:
        raise HTTPException(status_code=422, detail="RSI thresholds must be between 0 and 100 (exclusive)")
    if oversold >= overbought:
        raise HTTPException(status_code=422, detail="RSI oversold must be less than overbought")

    macd_fast = body.macd_fast if body.macd_fast is not None else current["macd_fast"]
    macd_slow = body.macd_slow if body.macd_slow is not None else current["macd_slow"]
    if macd_fast >= macd_slow:
        raise HTTPException(status_code=422, detail="MACD fast period must be less than slow period")


@app.get("/settings")
def get_settings():
    conn = get_connection()
    row = conn.execute("SELECT * FROM indicator_settings").fetchone()
    conn.close()
    result = dict(row)
    result.pop("id", None)
    return result


@app.put("/settings")
def update_settings(body: SettingsUpdate):
    conn = get_connection()
    current = dict(conn.execute("SELECT * FROM indicator_settings").fetchone())

    _validate_settings(body, current)

    updates = body.dict(exclude_none=True)
    if not updates:
        conn.close()
        return get_settings()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE indicator_settings SET {set_clause} WHERE id = 1",
        list(updates.values()),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM indicator_settings").fetchone()
    conn.close()
    result = dict(row)
    result.pop("id", None)
    return result


@app.post("/fetch/run")
def trigger_fetch():
    fetch()
    return {"status": "ok"}


@app.get("/tickers")
def list_tickers():
    conn = get_connection()
    rows = conn.execute("SELECT id, symbol FROM tickers ORDER BY symbol").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/prices/{ticker}")
def get_prices(
    ticker: str,
    timeframe: str = Query("1d"),
    include_sma: bool = Query(False, alias="sma"),
    include_rsi: bool = Query(False, alias="rsi"),
    include_macd: bool = Query(False, alias="macd"),
):
    if timeframe not in TIMEFRAME_CONFIG:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported timeframe: {timeframe}. Supported: {', '.join(TIMEFRAME_CONFIG)}",
        )

    symbol = ticker.upper()
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    ticker_id = row["id"]

    # On-demand fetch for intraday timeframes (daily handled by scheduler).
    ensure_fresh(ticker_id, symbol, timeframe)

    rows = conn.execute(
        """
        SELECT datetime, open, high, low, close, volume
        FROM prices
        WHERE ticker_id = ? AND timeframe = ?
        ORDER BY datetime ASC
        """,
        (ticker_id, timeframe),
    ).fetchall()

    # Read stored settings if any indicator is requested.
    settings = None
    if include_sma or include_rsi or include_macd:
        settings = conn.execute(
            "SELECT * FROM indicator_settings"
        ).fetchone()

    conn.close()

    data = [dict(r) for r in rows]

    closes = [r["close"] for r in data]

    if include_sma:
        sma_values = sma(closes, settings["sma_window"])
        for row_dict, sma_val in zip(data, sma_values):
            row_dict["sma"] = sma_val

    if include_rsi:
        rsi_values = rsi(closes, settings["rsi_window"])
        for row_dict, rsi_val in zip(data, rsi_values):
            row_dict["rsi"] = rsi_val

    if include_macd:
        macd_line, signal_line, hist = macd(
            closes,
            fast=settings["macd_fast"],
            slow=settings["macd_slow"],
            signal=settings["macd_signal"],
        )
        for row_dict, m, s, h in zip(data, macd_line, signal_line, hist):
            row_dict["macd"] = m
            row_dict["macd_signal"] = s
            row_dict["macd_hist"] = h

    return data


@app.get("/backtest/sma-crossover")
def backtest_sma_crossover(ticker: str = Query("SPY")):
    symbol = ticker.upper()
    if symbol != "SPY":
        raise HTTPException(
            status_code=422,
            detail="Only SPY is supported for backtesting in this milestone",
        )

    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    ticker_id = row["id"]
    bars = conn.execute(
        """
        SELECT datetime, open, high, low, close, volume
        FROM prices
        WHERE ticker_id = ? AND timeframe = '1d'
        ORDER BY datetime ASC
        """,
        (ticker_id,),
    ).fetchall()

    settings = conn.execute("SELECT sma_window FROM indicator_settings").fetchone()
    conn.close()

    sma_window = settings["sma_window"]
    data = [dict(r) for r in bars]

    if len(data) < sma_window + 1:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough data to backtest: have {len(data)} bars, need at least {sma_window + 1} for SMA window {sma_window}",
        )

    return run_backtest(data, sma_window)


@app.get("/signals/sma-crossover")
def signals_sma_crossover(ticker: str = Query("SPY")):
    symbol = ticker.upper()
    if symbol != "SPY":
        raise HTTPException(
            status_code=422,
            detail="Only SPY is supported for signals in this milestone",
        )

    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    ticker_id = row["id"]
    bars = conn.execute(
        """
        SELECT datetime, open, high, low, close, volume
        FROM prices
        WHERE ticker_id = ? AND timeframe = '1d'
        ORDER BY datetime ASC
        """,
        (ticker_id,),
    ).fetchall()

    settings = conn.execute("SELECT sma_window FROM indicator_settings").fetchone()
    conn.close()

    sma_window = settings["sma_window"]
    data = [dict(r) for r in bars]

    if len(data) < sma_window + 1:
        return []

    return extract_signals(data, sma_window)


@app.get("/dividends/{ticker}")
def get_dividends(ticker: str):
    symbol = ticker.upper()
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    rows = conn.execute(
        """
        SELECT date, amount FROM dividends
        WHERE ticker_id = ?
        ORDER BY date ASC
        """,
        (row["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/splits/{ticker}")
def get_splits(ticker: str):
    symbol = ticker.upper()
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    rows = conn.execute(
        """
        SELECT date, ratio FROM splits
        WHERE ticker_id = ?
        ORDER BY date ASC
        """,
        (row["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/fundamentals/{ticker}")
def get_fundamentals(ticker: str):
    symbol = ticker.upper()
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    fund = conn.execute(
        """
        SELECT market_cap, sector, industry, pe_ratio, last_updated
        FROM fundamentals
        WHERE ticker_id = ?
        """,
        (row["id"],),
    ).fetchone()
    conn.close()

    if fund is None:
        return {}

    return dict(fund)
