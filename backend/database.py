import sqlite3
from datetime import date, timedelta
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

        CREATE TABLE IF NOT EXISTS prices (
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            timeframe TEXT    NOT NULL DEFAULT '1d',
            datetime  TEXT    NOT NULL,
            open      REAL   NOT NULL,
            high      REAL   NOT NULL,
            low       REAL   NOT NULL,
            close     REAL   NOT NULL,
            volume    INTEGER NOT NULL,
            PRIMARY KEY (ticker_id, timeframe, datetime)
        );

        CREATE TABLE IF NOT EXISTS indicator_settings (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            sma_window      INTEGER NOT NULL DEFAULT 20,
            sma_color       TEXT    NOT NULL DEFAULT '#2962FF',
            rsi_window      INTEGER NOT NULL DEFAULT 14,
            rsi_overbought  REAL    NOT NULL DEFAULT 70,
            rsi_oversold    REAL    NOT NULL DEFAULT 30,
            rsi_color       TEXT    NOT NULL DEFAULT '#E91E63'
        );

        INSERT OR IGNORE INTO indicator_settings (id) VALUES (1);
    """)

    # Migrate from daily_prices to prices if the old table exists.
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if "daily_prices" in tables:
        conn.execute("""
            INSERT OR IGNORE INTO prices
                (ticker_id, timeframe, datetime, open, high, low, close, volume)
            SELECT ticker_id, '1d', date, open, high, low, close, volume
            FROM daily_prices
        """)
        conn.execute("DROP TABLE daily_prices")
        conn.commit()

    # Seed starter tickers.
    for symbol in ("SPY", "AAPL", "QQQ"):
        conn.execute(
            "INSERT OR IGNORE INTO tickers (symbol) VALUES (?)", (symbol,)
        )
    conn.commit()
    conn.close()


def _last_expected_trading_day() -> date:
    """Return the most recent weekday (Mon-Fri) that has fully closed.

    If today is a weekday, the last completed trading day is yesterday
    (today's bar isn't final until market close).  Walk backward over
    weekends to land on a Friday.
    """
    day = date.today() - timedelta(days=1)
    while day.weekday() >= 5:  # 5=Saturday, 6=Sunday
        day -= timedelta(days=1)
    return day


def is_data_stale() -> tuple[bool, str, str]:
    """Check if cached daily price data is stale.

    Returns (is_stale, latest_cached_date, expected_date).
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(datetime) AS latest FROM prices WHERE timeframe = '1d'"
    ).fetchone()
    conn.close()

    expected = _last_expected_trading_day()

    if row["latest"] is None:
        return True, "(empty)", str(expected)

    latest = row["latest"]
    return latest < str(expected), latest, str(expected)
