from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection, init_db
from indicators import sma, rsi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)

init_db()


@app.get("/tickers")
def list_tickers():
    conn = get_connection()
    rows = conn.execute("SELECT id, symbol FROM tickers ORDER BY symbol").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/prices/{ticker}")
def get_prices(
    ticker: str,
    sma_window: int | None = Query(None, alias="sma", gt=0),
    rsi_window: int | None = Query(None, alias="rsi", gt=0),
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
    conn.close()

    data = [dict(r) for r in rows]

    closes = [r["close"] for r in data]

    if sma_window is not None:
        sma_values = sma(closes, sma_window)
        for row_dict, sma_val in zip(data, sma_values):
            row_dict["sma"] = sma_val

    if rsi_window is not None:
        rsi_values = rsi(closes, rsi_window)
        for row_dict, rsi_val in zip(data, rsi_values):
            row_dict["rsi"] = rsi_val

    return data
