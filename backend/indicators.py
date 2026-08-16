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
