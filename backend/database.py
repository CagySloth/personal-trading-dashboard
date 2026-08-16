import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "market_data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tickers (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            date      TEXT    NOT NULL,
            open      REAL   NOT NULL,
            high      REAL   NOT NULL,
            low       REAL   NOT NULL,
            close     REAL   NOT NULL,
            volume    INTEGER NOT NULL,
            PRIMARY KEY (ticker_id, date)
        );
    """)
    # Seed starter tickers.
    for symbol in ("SPY", "AAPL", "QQQ"):
        conn.execute(
            "INSERT OR IGNORE INTO tickers (symbol) VALUES (?)", (symbol,)
        )
    conn.commit()
    conn.close()
