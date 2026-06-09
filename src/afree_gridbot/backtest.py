from dataclasses import dataclass

from .grid import GridConfig, build_grid_levels


@dataclass(frozen=True)
class BacktestResult:
    start_price: float
    end_price: float
    levels_crossed: int
    estimated_fees: float
    gross_score: float
    net_score: float


def run_simple_grid_backtest(
    prices: list[float],
    config: GridConfig,
    order_size: float,
    fee_rate: float = 0.001,
) -> BacktestResult:
    """Run a tiny research-only grid score over a price series.

    This is intentionally not a live trading engine. It counts how many grid
    levels were crossed between consecutive prices and estimates fees for those
    hypothetical fills.
    """
    if len(prices) < 2:
        raise ValueError("at least two prices are required")
    if order_size <= 0:
        raise ValueError("order_size must be positive")
    if fee_rate < 0:
        raise ValueError("fee_rate cannot be negative")

    levels = build_grid_levels(config)
    crossed = 0

    for previous, current in zip(prices, prices[1:]):
        low = min(previous, current)
        high = max(previous, current)
        crossed += sum(1 for level in levels if low < level <= high)

    estimated_fees = crossed * order_size * fee_rate
    gross_score = crossed * order_size
    net_score = gross_score - estimated_fees

    return BacktestResult(
        start_price=prices[0],
        end_price=prices[-1],
        levels_crossed=crossed,
        estimated_fees=round(estimated_fees, 8),
        gross_score=round(gross_score, 8),
        net_score=round(net_score, 8),
    )
