def sma(closes: list[float], window: int) -> list[float | None]:
    """Compute Simple Moving Average.

    Returns a list the same length as *closes*.  The first *window - 1*
    entries are None (not enough data); every subsequent entry is the
    arithmetic mean of the preceding *window* closes (inclusive).
    """
    result: list[float | None] = []
    for i in range(len(closes)):
        if i < window - 1:
            result.append(None)
        else:
            avg = sum(closes[i - window + 1 : i + 1]) / window
            result.append(round(avg, 4))
    return result


def rsi(closes: list[float], window: int = 14) -> list[float | None]:
    """Compute Relative Strength Index using Wilder's smoothing.

    Returns a list the same length as *closes*.  The first *window*
    entries are None (need *window* price changes, i.e. *window + 1*
    prices, before the first RSI value).
    """
    if len(closes) < window + 1:
        return [None] * len(closes)

    result: list[float | None] = [None] * window

    # Compute price changes.
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Seed: simple average of first *window* gains and losses.
    gains = [max(d, 0) for d in deltas[:window]]
    losses = [max(-d, 0) for d in deltas[:window]]
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - 100 / (1 + rs), 4))

    # Wilder's smoothing for subsequent values.
    for i in range(window, len(deltas)):
        gain = max(deltas[i], 0)
        loss = max(-deltas[i], 0)
        avg_gain = (avg_gain * (window - 1) + gain) / window
        avg_loss = (avg_loss * (window - 1) + loss) / window

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - 100 / (1 + rs), 4))

    return result
