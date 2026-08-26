"""Minimal SMA-crossover backtesting engine."""

from indicators import sma


def sma_crossover(bars: list[dict], sma_window: int, cost_pct: float = 0.0) -> dict:
    """Simulate an SMA-crossover strategy on daily bars.

    Strategy rules:
      - Buy (fully long) when close > SMA on that day.
      - Sell (fully flat) when close < SMA on that day.
      - Trades execute at the closing price of the signal day.

    Args:
        bars: list of dicts with at least 'datetime' and 'close' keys,
              in chronological order.
        sma_window: SMA look-back window (reuses the existing SMA function).
        cost_pct: per-trade commission as a fraction (e.g. 0.001 = 0.1%),
                  applied to trade value at both entry and exit.

    Returns a dict with:
        trades:  list of {entry_date, entry_price, exit_date, exit_price, return_pct}
        equity:  list of {date, value} representing portfolio value over time
    """
    closes = [b["close"] for b in bars]
    sma_values = sma(closes, sma_window)

    starting_cash = 10_000.0
    cash = starting_cash
    shares = 0.0
    in_position = False
    entry_date = None
    entry_price = None

    trades: list[dict] = []
    equity: list[dict] = []

    for i, bar in enumerate(bars):
        price = bar["close"]
        sma_val = sma_values[i]

        # Record portfolio value each day.
        portfolio_value = cash + shares * price
        equity.append({"date": bar["datetime"], "value": round(portfolio_value, 2)})

        # No signal until SMA is available.
        if sma_val is None:
            continue

        if not in_position and price > sma_val:
            # Buy signal: invest all cash, minus entry commission.
            cost = cash * cost_pct
            investable = cash - cost
            shares = investable / price
            cash = 0.0
            in_position = True
            entry_date = bar["datetime"]
            entry_price = price

        elif in_position and price < sma_val:
            # Sell signal: liquidate entire position, minus exit commission.
            gross = shares * price
            cost = gross * cost_pct
            cash = gross - cost
            shares = 0.0
            in_position = False
            ret = (price - entry_price) / entry_price * 100
            trades.append({
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_date": bar["datetime"],
                "exit_price": price,
                "return_pct": round(ret, 4),
            })
            entry_date = None
            entry_price = None

    return {"trades": trades, "equity": equity}


def extract_signals(bars: list[dict], sma_window: int) -> list[dict]:
    """Extract buy/sell signal events from the SMA-crossover simulation.

    Returns a flat list of {date, type, price} dicts, one per signal,
    in chronological order.
    """
    sim = sma_crossover(bars, sma_window)
    signals: list[dict] = []
    for trade in sim["trades"]:
        signals.append({
            "date": trade["entry_date"],
            "type": "buy",
            "price": trade["entry_price"],
        })
        signals.append({
            "date": trade["exit_date"],
            "type": "sell",
            "price": trade["exit_price"],
        })
    return signals


def _max_drawdown(equity: list[dict]) -> float:
    """Compute maximum drawdown (%) from an equity series."""
    if not equity:
        return 0.0
    peak = equity[0]["value"]
    max_dd = 0.0
    for point in equity:
        v = point["value"]
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)


def _buy_and_hold(bars: list[dict]) -> dict:
    """Compute buy-and-hold metrics over the same bar range."""
    first_close = bars[0]["close"]
    last_close = bars[-1]["close"]
    total_return = (last_close - first_close) / first_close * 100

    # Build equity series for drawdown calculation.
    starting_value = 10_000.0
    shares = starting_value / first_close
    equity = []
    for bar in bars:
        equity.append({
            "date": bar["datetime"],
            "value": round(shares * bar["close"], 2),
        })

    return {
        "total_return_pct": round(total_return, 4),
        "max_drawdown_pct": _max_drawdown(equity),
        "start_date": bars[0]["datetime"],
        "end_date": bars[-1]["datetime"],
    }


def _build_result(sim: dict) -> dict:
    """Build metrics + trade log + equity from a simulation result."""
    trades = sim["trades"]
    equity = sim["equity"]

    start_value = equity[0]["value"] if equity else 0
    end_value = equity[-1]["value"] if equity else 0
    total_return = (end_value - start_value) / start_value * 100 if start_value else 0

    winning = sum(1 for t in trades if t["return_pct"] > 0)
    win_rate = (winning / len(trades) * 100) if trades else 0

    return {
        "strategy": {
            "total_return_pct": round(total_return, 4),
            "max_drawdown_pct": _max_drawdown(equity),
            "num_trades": len(trades),
            "win_rate_pct": round(win_rate, 4),
        },
        "trades": trades,
        "equity": equity,
    }


DEFAULT_COST_PCT = 0.001  # 0.1% per trade


def run_backtest(bars: list[dict], sma_window: int) -> dict:
    """Run the SMA-crossover backtest and return full results with metrics.

    Returns a dict with:
        frictionless: {strategy, trades, equity} — cost_pct=0
        cost_adjusted: {strategy, trades, equity} — cost_pct=0.1%
        buy_and_hold: {total_return_pct, max_drawdown_pct, start_date, end_date}
    """
    frictionless_sim = sma_crossover(bars, sma_window, cost_pct=0.0)
    cost_adjusted_sim = sma_crossover(bars, sma_window, cost_pct=DEFAULT_COST_PCT)

    frictionless = _build_result(frictionless_sim)
    cost_adjusted = _build_result(cost_adjusted_sim)

    bnh_metrics = _buy_and_hold(bars)

    return {
        "frictionless": frictionless,
        "cost_adjusted": cost_adjusted,
        "buy_and_hold": bnh_metrics,
    }
