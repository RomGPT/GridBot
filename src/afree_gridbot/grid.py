from dataclasses import dataclass


@dataclass(frozen=True)
class GridConfig:
    lower_price: float
    upper_price: float
    grid_count: int

    def validate(self) -> None:
        if self.lower_price <= 0:
            raise ValueError("lower_price must be positive")
        if self.upper_price <= self.lower_price:
            raise ValueError("upper_price must be greater than lower_price")
        if self.grid_count < 2:
            raise ValueError("grid_count must be at least 2")


def build_grid_levels(config: GridConfig) -> list[float]:
    """Return evenly spaced grid levels, including lower and upper bounds."""
    config.validate()
    step = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    return [round(config.lower_price + step * index, 8) for index in range(config.grid_count)]
