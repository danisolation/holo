"""Paper trade business logic: state machine, P&L calculation, position sizing.

Pure Python functions — no DB, no async. Consumed by Phase 23 scheduler
and Phase 24 API.

PT-02: State machine transitions
PT-03: Partial TP with breakeven SL
PT-05: Position sizing with 100-lot rounding
PT-07: P&L calculation with partial TP support
"""
from decimal import Decimal

from app.models.paper_trade import TradeStatus, TradeDirection


# --- State Machine (PT-02) ---

VALID_TRANSITIONS: dict[TradeStatus, set[TradeStatus]] = {
    TradeStatus.PENDING: {TradeStatus.ACTIVE, TradeStatus.CLOSED_MANUAL},
    TradeStatus.ACTIVE: {
        TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_SL,
        TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL,
    },
    TradeStatus.PARTIAL_TP: {
        TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
        TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL,
    },
    TradeStatus.CLOSED_TP2: set(),
    TradeStatus.CLOSED_SL: set(),
    TradeStatus.CLOSED_TIMEOUT: set(),
    TradeStatus.CLOSED_MANUAL: set(),
}


def validate_transition(current: TradeStatus, target: TradeStatus) -> bool:
    """Check if a state transition is valid.

    Returns True if transition is allowed, False otherwise.
    """
    return target in VALID_TRANSITIONS.get(current, set())


# --- P&L Calculation (PT-07) ---

def calculate_pnl(
    direction: str,
    entry_price: Decimal,
    quantity: int,
    partial_exit_price: Decimal | None,
    closed_quantity: int,
    exit_price: Decimal,
) -> tuple[Decimal, float]:
    """Calculate total P&L for a paper trade including partial TP.

    Handles two-leg trades: leg 1 (partial TP at TP1) + leg 2 (final exit).
    BEARISH direction uses inverted math (profit when price drops).

    Args:
        direction: "long" or "bearish"
        entry_price: Entry price (Decimal)
        quantity: Total position size in shares
        partial_exit_price: TP1 price if partial TP happened, else None
        closed_quantity: Shares closed at TP1 (0 if no partial TP)
        exit_price: Final exit price for remaining shares

    Returns:
        (pnl_vnd: Decimal, pnl_pct: float) tuple
    """
    remaining = quantity - closed_quantity

    if direction == "long":
        leg1 = (
            (partial_exit_price - entry_price) * closed_quantity
            if closed_quantity > 0 and partial_exit_price
            else Decimal("0")
        )
        leg2 = (exit_price - entry_price) * remaining
    else:
        # BEARISH: inverted — profit when price drops
        leg1 = (
            (entry_price - partial_exit_price) * closed_quantity
            if closed_quantity > 0 and partial_exit_price
            else Decimal("0")
        )
        leg2 = (entry_price - exit_price) * remaining

    total_pnl = leg1 + leg2
    total_cost = entry_price * quantity
    pnl_pct = float(total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    return total_pnl, round(pnl_pct, 2)


# --- Position Sizing (PT-05) ---

def calculate_position_size(
    capital: Decimal,
    allocation_pct: int,
    entry_price: Decimal,
) -> int:
    """Calculate position size in shares, rounded to 100-share lots.

    VN exchange requires 100-share minimum lots. Returns 0 if capital
    cannot afford even 100 shares at the given allocation.

    Args:
        capital: Total virtual capital (Decimal, VND)
        allocation_pct: AI recommended allocation percentage (1-100)
        entry_price: Expected entry price per share (Decimal, VND)

    Returns:
        Number of shares (int), always a multiple of 100 or 0
    """
    allocated = capital * allocation_pct / 100
    raw_shares = int(allocated / entry_price)
    lot_rounded = (raw_shares // 100) * 100

    # Minimum 100 shares if raw calculation > 0 and can actually afford 100
    if lot_rounded == 0 and raw_shares >= 1:
        if allocated >= entry_price * 100:
            lot_rounded = 100

    return lot_rounded


# --- Partial Take Profit (PT-03) ---

def apply_partial_tp(trade, tp1_price: Decimal) -> None:
    """Apply partial take-profit: close ~50%, move SL to breakeven.

    Mutates trade in-place. Caller must commit DB session.

    Rules:
    - Half quantity rounded DOWN to 100-share boundary (conservative)
    - If half rounds to 0 (e.g. qty=100), close all at TP1
    - SL moved to entry price (breakeven) for remaining position

    Args:
        trade: PaperTrade instance (or mock with same attributes)
        tp1_price: Price at which TP1 was hit

    Raises:
        ValueError: If trade is not in ACTIVE status
    """
    if trade.status != TradeStatus.ACTIVE:
        raise ValueError(
            f"Cannot apply partial TP from status {trade.status}"
        )

    half_qty = trade.quantity // 2
    # Round down to 100-share lot boundary
    half_qty = (half_qty // 100) * 100
    # If half rounds to 0 (qty <= 100), close all at TP1
    if half_qty == 0:
        half_qty = trade.quantity

    trade.status = TradeStatus.PARTIAL_TP
    trade.closed_quantity = half_qty
    trade.partial_exit_price = tp1_price
    trade.adjusted_stop_loss = trade.entry_price  # Breakeven
