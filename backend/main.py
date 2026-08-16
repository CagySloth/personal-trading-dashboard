from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection, init_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)

init_db()


@app.get("/prices/{ticker}")
def get_prices(ticker: str):
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

    return [dict(r) for r in rows]
