"""Fetch daily OHLCV data for all tickers and upsert into SQLite."""

import yfinance as yf
from database import get_connection, init_db


def fetch() -> None:
    init_db()
    conn = get_connection()

    tickers = conn.execute("SELECT id, symbol FROM tickers ORDER BY id").fetchall()

    for ticker_row in tickers:
        ticker_id = ticker_row["id"]
        symbol = ticker_row["symbol"]

        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max")

        if df.empty:
            print(f"No data returned for {symbol}")
            continue

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
        print(f"Upserted {len(rows)} rows for {symbol}")

    conn.close()


if __name__ == "__main__":
    fetch()
