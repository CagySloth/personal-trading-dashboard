import logging
import re
import threading
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_connection, init_db, is_data_stale
from backtest import run_backtest, extract_signals
from fetch import fetch, ensure_fresh, TIMEFRAME_CONFIG
from indicators import sma, rsi

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_job(fetch, "cron", hour=16, minute=30, timezone="US/Eastern", id="daily_fetch")


def _startup_staleness_check() -> None:
    stale, latest, expected = is_data_stale()
    if stale:
        logger.info(
            "Data is stale (latest: %s, expected: %s) — running catch-up fetch",
            latest, expected,
        )
        fetch()
        logger.info("Catch-up fetch complete")
    else:
        logger.info("Data is current (latest: %s) — skipping fetch", latest)


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


def _validate_settings(body: SettingsUpdate, current: dict) -> None:
    """Validate settings fields, raising HTTPException on invalid input."""
    for field in ("sma_window", "rsi_window"):
        val = getattr(body, field)
        if val is not None and val < 1:
            raise HTTPException(status_code=422, detail=f"{field} must be >= 1")

    for field in ("sma_color", "rsi_color"):
        val = getattr(body, field)
        if val is not None and not HEX_COLOR_RE.match(val):
            raise HTTPException(status_code=422, detail="Color must be a hex string like #RRGGBB")

    overbought = body.rsi_overbought if body.rsi_overbought is not None else current["rsi_overbought"]
    oversold = body.rsi_oversold if body.rsi_oversold is not None else current["rsi_oversold"]

    if oversold <= 0 or overbought >= 100:
        raise HTTPException(status_code=422, detail="RSI thresholds must be between 0 and 100 (exclusive)")
    if oversold >= overbought:
        raise HTTPException(status_code=422, detail="RSI oversold must be less than overbought")


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
    if include_sma or include_rsi:
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
