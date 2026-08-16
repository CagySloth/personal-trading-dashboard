"""Fetch daily OHLCV data for SPY and upsert into SQLite."""

import yfinance as yf
from database import get_connection, init_db

SYMBOL = "SPY"


def fetch() -> None:
    init_db()

    ticker = yf.Ticker(SYMBOL)
    df = ticker.history(period="max")

    if df.empty:
        print(f"No data returned for {SYMBOL}")
        return

    conn = get_connection()

    # Ensure the ticker row exists and get its id.
    conn.execute("INSERT OR IGNORE INTO tickers (symbol) VALUES (?)", (SYMBOL,))
    conn.commit()
    row = conn.execute(
        "SELECT id FROM tickers WHERE symbol = ?", (SYMBOL,)
    ).fetchone()
    ticker_id = row["id"]

    # Upsert daily prices.
    rows = []
    for date, r in df.iterrows():
        rows.append((
            ticker_id,
            date.strftime("%Y-%m-%d"),
            round(r["Open"], 4),
            round(r["High"], 4),
            round(r["Low"], 4),
            round(r["Close"], 4),
            int(r["Volume"]),
        ))

    conn.executemany(
        """
        INSERT INTO daily_prices (ticker_id, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker_id, date) DO UPDATE SET
            open   = excluded.open,
            high   = excluded.high,
            low    = excluded.low,
            close  = excluded.close,
            volume = excluded.volume
        """,
        rows,
    )
    conn.commit()
    print(f"Upserted {len(rows)} rows for {SYMBOL}")
    conn.close()


if __name__ == "__main__":
    fetch()
