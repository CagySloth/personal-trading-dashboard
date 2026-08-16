import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection, init_db
from indicators import sma, rsi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

init_db()


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


@app.get("/tickers")
def list_tickers():
    conn = get_connection()
    rows = conn.execute("SELECT id, symbol FROM tickers ORDER BY symbol").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/prices/{ticker}")
def get_prices(
    ticker: str,
    include_sma: bool = Query(False, alias="sma"),
    include_rsi: bool = Query(False, alias="rsi"),
):
    symbol = ticker.upper()
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (symbol,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")

    ticker_id = row["id"]
    rows = conn.execute(
        """
        SELECT date, open, high, low, close, volume
        FROM daily_prices
        WHERE ticker_id = ?
        ORDER BY date ASC
        """,
        (ticker_id,),
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
