from afree_gridbot import GridConfig, run_simple_grid_backtest


prices = [100, 103, 101, 106, 109, 104, 111]
config = GridConfig(lower_price=95, upper_price=115, grid_count=6)
result = run_simple_grid_backtest(prices, config, order_size=10, fee_rate=0.001)

print(result)
