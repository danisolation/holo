"""Shared analytics utilities used by both backtest and paper-trade analytics services."""
from app.models.paper_trade import TradeStatus


CLOSED_STATUSES = [
    TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
    TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL,
]


def calc_win_rate(wins: int, total: int) -> float:
    return round(wins / total * 100, 2) if total > 0 else 0.0


def calc_pnl_pct(pnl: float, capital: float) -> float:
    return round(pnl / capital * 100, 2) if capital > 0 else 0.0


def calc_avg_pnl(total_pnl: float, count: int) -> float:
    return round(total_pnl / count, 2) if count > 0 else 0.0


def calc_max_drawdown(equity_points: list[float]) -> tuple[float, float]:
    """Compute max drawdown (VND, %) from an equity curve.

    Returns (max_dd_vnd, max_dd_pct) where both are <= 0.
    """
    max_dd_vnd = 0.0
    max_dd_pct = 0.0
    peak = 0.0
    for value in equity_points:
        if value > peak:
            peak = value
        drawdown = value - peak
        if drawdown < max_dd_vnd:
            max_dd_vnd = drawdown
            max_dd_pct = round(drawdown / peak * 100, 2) if peak > 0 else 0.0
    return max_dd_vnd, max_dd_pct
