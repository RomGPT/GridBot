from educational_gridbot import GridConfig, build_grid_levels, run_simple_grid_backtest


def test_build_grid_levels_includes_bounds():
    levels = build_grid_levels(GridConfig(lower_price=100, upper_price=120, grid_count=5))
    assert levels == [100, 105, 110, 115, 120]


def test_simple_backtest_counts_crossed_levels():
    result = run_simple_grid_backtest(
        prices=[100, 106, 101, 111],
        config=GridConfig(lower_price=95, upper_price=115, grid_count=5),
        order_size=10,
        fee_rate=0.001,
    )
    assert result.levels_crossed > 0
    assert result.net_score < result.gross_score
