"""Dip Hunter Bot V3.0 implementation.

This module defines the DipHunterBot trading system together with helper
components that follow the architecture described in the specification.
The bot is structured for clarity and testability and does not perform any
network operations. Instead, data providers and execution backends are
abstracted so the bot can be integrated with real services (e.g. Bybit API)
by supplying concrete dependencies in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class DipStrength(Enum):
    """Levels of dip intensity used for position sizing."""

    MINOR = auto()
    MEDIUM = auto()
    MAJOR = auto()


class OrderUrgency(Enum):
    """Order urgency used by the commission optimiser."""

    LOW = auto()
    NORMAL = auto()
    HIGH = auto()


@dataclass
class DipSignal:
    """Represents a trading signal produced by dip detection."""

    pair: str
    strength: float
    drop_percent: float
    entry_price: float
    stop_loss: float
    targets: Sequence[float]
    technical_score: int
    dip_type: DipStrength
    position_size: float = 0.0


@dataclass
class Order:
    """Simplified order representation for optimisation."""

    symbol: str
    side: str
    price: float
    quantity: float
    urgency: OrderUrgency = OrderUrgency.NORMAL
    time_in_force: Optional[str] = None


@dataclass
class Position:
    """Active trading position."""

    id: str
    symbol: str
    entry_price: float
    quantity: float
    dip_type: DipStrength


@dataclass
class DailyStats:
    """Metrics used by the anti-overtrading system."""

    trades_count: int
    pnl_percent: float
    last_loss_time: Optional[datetime]


class MarketDataProvider:
    """Abstract market data dependency.

    Real integrations should subclass this provider and implement the
    required methods.
    """

    def list_top_pairs(self, count: int) -> Sequence[str]:
        raise NotImplementedError

    def get_price_change(self, pair: str, timeframe: str) -> float:
        raise NotImplementedError

    def get_volume(self, pair: str, timeframe: str) -> float:
        raise NotImplementedError

    def get_average_volume(self, pair: str, timeframe: str, periods: int) -> float:
        raise NotImplementedError

    def get_rsi(self, pair: str, timeframe: str) -> float:
        raise NotImplementedError

    def get_price(self, pair: str) -> float:
        raise NotImplementedError

    def get_bollinger_lower(self, pair: str, timeframe: str) -> float:
        raise NotImplementedError

    def get_support_distance(self, pair: str, price: float) -> float:
        raise NotImplementedError

    def get_macd_divergence(self, pair: str) -> bool:
        raise NotImplementedError


class ExecutionBackend:
    """Abstract execution backend for the trading bot."""

    def place_limit_order(self, order: Order) -> str:
        raise NotImplementedError

    def place_take_profit_order(self, order: Order) -> None:
        raise NotImplementedError

    def place_stop_loss_order(self, order: Order) -> None:
        raise NotImplementedError

    def execute_scaled_orders(self, base_order: Order, portions: int) -> None:
        raise NotImplementedError

    def queue_for_batching(self, order: Order) -> None:
        raise NotImplementedError


class RiskController:
    """Risk management utilities used by the bot."""

    def validate_risk_parameters(self) -> bool:
        raise NotImplementedError


class TimeProvider:
    """Dependency that returns current time for easier testing."""

    def now(self) -> datetime:
        return datetime.utcnow()


class DipHunterBot:
    """Implements the multi-layer dip trading logic."""

    def __init__(
        self,
        market_data: MarketDataProvider,
        execution: ExecutionBackend,
        risk_controller: RiskController,
        time_provider: Optional[TimeProvider] = None,
        account_balance: float = 10_000.0,
        max_position_size: float = 1_000.0,
    ) -> None:
        self.strategy = "MULTI_LAYER_DIP_BUYING"
        self.market_data = market_data
        self.execution = execution
        self.risk_controller = risk_controller
        self.time_provider = time_provider or TimeProvider()
        self.account_balance = account_balance
        self.max_position_size = max_position_size
        self.max_concurrent_positions = 5
        self.commission_rate = 0.055
        self.top_50_pairs = list(self.market_data.list_top_pairs(50))

    # ------------------------------------------------------------------
    # Dip detection
    # ------------------------------------------------------------------
    def detect_dips(self) -> List[DipSignal]:
        """Scan the market and return a sorted list of dip signals."""

        criteria = {
            "timeframes": ["5m", "15m", "1h"],
            "drop_thresholds": {"minor": -3, "medium": -7, "major": -15},
            "volume_spike": 1.5,
            "rsi_oversold": 30,
        }

        signals: List[DipSignal] = []
        for pair in self.top_50_pairs:
            if self.is_valid_dip(pair, criteria):
                strength = self.calculate_dip_strength(pair, criteria)
                entry_price = self.get_optimal_entry(pair)
                stop_loss = self.calculate_stop_loss(pair, entry_price)
                targets = self.calculate_targets(pair, entry_price)
                dip_type = self.classify_drop(strength)
                technical_score = self.technical_confluence(pair)
                drop_percent = strength
                signals.append(
                    DipSignal(
                        pair=pair,
                        strength=strength,
                        drop_percent=drop_percent,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        technical_score=technical_score,
                        dip_type=dip_type,
                    )
                )

        return sorted(signals, key=lambda signal: signal.strength, reverse=True)

    # ------------------------------------------------------------------
    # Validation layers
    # ------------------------------------------------------------------
    def is_valid_dip(self, pair: str, criteria: Dict) -> bool:
        if not self.macro_filter_check():
            return False

        if not self.structure_analysis(pair):
            return False

        tech_score = self.technical_confluence(pair)
        if tech_score < 3:
            return False

        if self.onchain_analysis(pair) < 0:
            return False

        if not self.microstructure_check(pair):
            return False

        return True

    def macro_filter_check(self) -> bool:
        # Placeholder macro filter always passes.
        return True

    def structure_analysis(self, pair: str) -> bool:
        # Simplistic structure analysis: ensure support distance under 3%.
        price = self.market_data.get_price(pair)
        return self.market_data.get_support_distance(pair, price) <= 0.03

    def technical_confluence(self, pair: str) -> int:
        score = 0

        if self.market_data.get_rsi(pair, "1h") < 30:
            score += 1

        price = self.market_data.get_price(pair)
        bb_lower = self.market_data.get_bollinger_lower(pair, "1h")
        if price <= bb_lower * 1.02:
            score += 1

        current_volume = self.market_data.get_volume(pair, "1h")
        avg_volume = self.market_data.get_average_volume(pair, "1h", 20)
        if current_volume > avg_volume * 1.5:
            score += 1

        if self.market_data.get_support_distance(pair, price) <= 0.01:
            score += 1

        if self.market_data.get_macd_divergence(pair):
            score += 1

        return score

    def onchain_analysis(self, pair: str) -> int:
        # Stand-in on-chain analysis returning neutral score.
        return 1

    def microstructure_check(self, pair: str) -> bool:
        # Simplified microstructure: reuse volume spike as liquidity proxy.
        current_volume = self.market_data.get_volume(pair, "5m")
        avg_volume = self.market_data.get_average_volume(pair, "5m", 12)
        return current_volume > avg_volume * 1.2

    # ------------------------------------------------------------------
    # Signal metrics
    # ------------------------------------------------------------------
    def calculate_dip_strength(self, pair: str, criteria: Dict) -> float:
        timeframe = criteria["timeframes"][0]
        return self.market_data.get_price_change(pair, timeframe)

    def classify_drop(self, drop_percent: float) -> DipStrength:
        if drop_percent >= -7:
            return DipStrength.MINOR
        if drop_percent >= -15:
            return DipStrength.MEDIUM
        return DipStrength.MAJOR

    def get_optimal_entry(self, pair: str) -> float:
        return self.market_data.get_price(pair)

    def calculate_stop_loss(self, pair: str, entry_price: float) -> float:
        return entry_price * 0.95

    def calculate_targets(self, pair: str, entry_price: float) -> List[float]:
        return [entry_price * (1 + p) for p in (0.03, 0.07, 0.15)]

    # ------------------------------------------------------------------
    # Position sizing and execution
    # ------------------------------------------------------------------
    def calculate_position_sizing(self, signal: DipSignal) -> float:
        base_risk = self.account_balance * 0.02

        multipliers = {
            DipStrength.MINOR: 0.5,
            DipStrength.MEDIUM: 1.0,
            DipStrength.MAJOR: 1.5,
        }

        position_multiplier = multipliers[signal.dip_type]

        if signal.technical_score >= 4:
            position_multiplier += 0.3

        risk_amount = base_risk * position_multiplier
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        if stop_distance == 0:
            return 0.0

        position_size = risk_amount / stop_distance
        position_size *= 1 - self.commission_rate * 2

        signal.position_size = min(position_size, self.max_position_size)
        return signal.position_size

    def execute_entry(self, signal: DipSignal, orderbook_depth: Dict[str, float]) -> None:
        target_size = signal.position_size
        slippage = orderbook_depth.get("slippage", 0.0)
        order_price = signal.entry_price * 1.001

        if slippage < 0.1:
            order = Order(
                symbol=signal.pair,
                side="Buy",
                price=order_price,
                quantity=target_size,
                urgency=OrderUrgency.LOW,
                time_in_force="PostOnly",
            )
            self.execution.place_limit_order(order)
        else:
            order = Order(
                symbol=signal.pair,
                side="Buy",
                price=signal.entry_price,
                quantity=target_size,
                urgency=OrderUrgency.HIGH,
            )
            self.execution.execute_scaled_orders(order, portions=5)

    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------
    def setup_risk_management(self, position: Position) -> None:
        if position.dip_type == DipStrength.MINOR:
            stop_percent = -0.05
        elif position.dip_type == DipStrength.MEDIUM:
            stop_percent = -0.08
        else:
            stop_percent = -0.12

        initial_stop = position.entry_price * (1 + stop_percent)
        targets = [
            {"percent": 0.03, "quantity": 0.3},
            {"percent": 0.07, "quantity": 0.4},
            {"percent": 0.15, "quantity": 0.3},
        ]

        for idx, target in enumerate(targets, 1):
            price = position.entry_price * (1 + target["percent"])
            quantity = position.quantity * target["quantity"]
            order = Order(
                symbol=position.symbol,
                side="Sell",
                price=price,
                quantity=quantity,
                time_in_force="GTC",
            )
            self.execution.place_take_profit_order(order)

        stop_order = Order(
            symbol=position.symbol,
            side="Sell",
            price=initial_stop,
            quantity=position.quantity,
            time_in_force="GTC",
        )
        self.execution.place_stop_loss_order(stop_order)

    def anti_overtrading_system(self, stats: DailyStats) -> Tuple[bool, str]:
        daily_limits = {
            "max_trades": 20,
            "max_loss_percent": -0.05,
            "cooldown_after_loss": timedelta(minutes=30),
            "max_concurrent": self.max_concurrent_positions,
        }

        if stats.trades_count >= daily_limits["max_trades"]:
            return False, "Daily trade limit reached"

        if stats.pnl_percent <= daily_limits["max_loss_percent"]:
            return False, "Daily loss limit reached"

        if stats.last_loss_time and (
            self.time_provider.now() - stats.last_loss_time
        ) < daily_limits["cooldown_after_loss"]:
            return False, "Cooling down after loss"

        return True, "OK"

    # ------------------------------------------------------------------
    # Commission optimisation
    # ------------------------------------------------------------------
    def minimize_commission_cost(self, orders: Iterable[Order]) -> List[str]:
        optimisations: List[str] = []

        for order in orders:
            if order.urgency == OrderUrgency.LOW:
                order.time_in_force = "PostOnly"
                order.price = self.adjust_for_maker_execution(order)
                optimisations.append(f"PostOnly used for {order.symbol}")
            elif order.quantity < self.get_min_efficient_size(order.symbol):
                self.execution.queue_for_batching(order)
                optimisations.append(f"Batched small order for {order.symbol}")
            elif order.quantity > self.get_large_order_threshold(order.symbol):
                self.execution.execute_scaled_orders(order, portions=5)
                optimisations.append(f"Scaled large order for {order.symbol}")

        return optimisations

    def adjust_for_maker_execution(self, order: Order) -> float:
        tick_size = self.get_tick_size(order.symbol)
        if order.side == "Buy":
            best_bid = order.price
            return best_bid + tick_size
        best_ask = order.price
        return max(best_ask - tick_size, 0.0)

    def get_min_efficient_size(self, symbol: str) -> float:
        return 1.0

    def get_large_order_threshold(self, symbol: str) -> float:
        return 100.0

    def get_tick_size(self, symbol: str) -> float:
        return 0.01

    # ------------------------------------------------------------------
    # Performance reporting and adaptive optimisation
    # ------------------------------------------------------------------
    def generate_performance_report(self, stats: Dict[str, object]) -> str:
        lines = [
            "🤖 DIP-HUNTER BOT Performance Report",
            "═══════════════════════════════════",
            "",
            f"📊 Trading Metrics:",
            f"• Win Rate: {stats['win_rate']:.1f}%",
            f"• Profit Factor: {stats['profit_factor']:.2f}",
            f"• Sharpe Ratio: {stats['sharpe_ratio']:.2f}",
            f"• Max Drawdown: {stats['max_drawdown']:.1f}%",
            "",
            "💰 Financial Results:",
            f"• Total Trades: {stats['total_trades']}",
            f"• Total P&L: {stats['total_pnl']:.2f} USDT",
            f"• ROI: {stats['roi']:.1f}%",
            f"• Avg Trade: {stats['avg_trade']:.2f} USDT",
            "",
            "🎯 Efficiency Metrics:",
            f"• Commission Paid: {stats['commission_paid']:.2f} USDT",
            f"• Commission Rate: {stats['commission_rate']:.3f}%",
            f"• Slippage: {stats['avg_slippage']:.2f}%",
            f"• Execution Speed: {stats['avg_exec_time']:.0f}ms",
            "",
            "🔝 Best Performers:",
        ]

        for pair, performance in stats.get("best_pairs", []):
            lines.append(f"• {pair}: +{performance:.1f}%")

        return "\n".join(lines)

    def adaptive_optimization(self, recent_performance: Dict[str, float]) -> Dict[str, float]:
        adjustments: Dict[str, float] = {}

        if recent_performance.get("false_signals", 0.0) > 0.4:
            adjustments["technical_threshold"] = 4
            adjustments["rsi_oversold"] = 25

        if recent_performance.get("missed_opportunities", 0.0) > 0.3:
            adjustments["technical_threshold"] = min(
                2, adjustments.get("technical_threshold", 5)
            )
            adjustments["volume_spike_threshold"] = 1.3

        market_vol = recent_performance.get("market_volatility", 0.0)
        if market_vol > 0.4:
            adjustments["position_multiplier"] = 0.7
        elif market_vol < 0.2:
            adjustments["position_multiplier"] = 1.3

        return adjustments

    # ------------------------------------------------------------------
    # Deployment checklist
    # ------------------------------------------------------------------
    def pre_deployment_checklist(self, checks: Dict[str, bool]) -> str:
        passed = sum(1 for state in checks.values() if state)
        total = len(checks)

        if passed == total:
            return "✅ All checks passed - Ready for deployment"

        failed = [name for name, state in checks.items() if not state]
        return f"❌ Failed checks: {', '.join(failed)}"

    def deploy_with_gradual_scaling(
        self,
        update_trading_limits: Callable[[Dict[str, int]], None],
        evaluate_stage_performance: Callable[[], Dict[str, int]],
        sleep: Callable[[int], None],
    ) -> List[str]:
        stages = [
            {"duration": "24h", "max_position": 100, "max_trades": 5},
            {"duration": "48h", "max_position": 300, "max_trades": 10},
            {"duration": "72h", "max_position": 500, "max_trades": 15},
            {"duration": "∞", "max_position": 1000, "max_trades": 20},
        ]

        logs: List[str] = []
        for idx, stage in enumerate(stages, start=1):
            logs.append(f"🚀 Deploying Stage {idx}: {stage}")
            update_trading_limits(stage)

            if stage["duration"] != "∞":
                duration = self._parse_duration(stage["duration"])
                sleep(duration)

                performance = evaluate_stage_performance()
                if performance.get("issues", 0) > 0:
                    logs.append(
                        f"⚠️ Issues detected in Stage {idx}. Manual review required."
                    )
                    break
            else:
                logs.append("🎯 Full deployment completed successfully!")

        return logs

    def _parse_duration(self, spec: str) -> int:
        unit = spec[-1]
        value = int(spec[:-1])
        if unit == "h":
            return value * 3600
        if unit == "m":
            return value * 60
        raise ValueError(f"Unsupported duration unit in {spec}")


class MarketDataManager:
    """Optimises websocket subscriptions for market data."""

    def __init__(self) -> None:
        self.ws_connections: Dict[str, object] = {}
        self.data_cache: Dict[str, object] = {}
        self.update_frequencies = {
            "price": 100,
            "orderbook": 1000,
            "klines": 5000,
        }

    def optimize_subscriptions(self, active_pairs: Sequence[str]) -> None:
        essential_pairs = set(active_pairs) | set(self.get_top_10_by_volume())

        for pair in list(self.ws_connections.keys()):
            if pair not in essential_pairs:
                self.ws_connections.pop(pair, None)

        for pair in essential_pairs:
            if pair not in self.ws_connections:
                self.ws_connections[pair] = self.create_ws_subscription(pair)

    def create_ws_subscription(self, pair: str) -> Dict[str, str]:
        return {"symbol": pair, "channels": ["ticker", "orderbook", "kline"]}

    def get_top_10_by_volume(self) -> List[str]:
        return [f"PAIR{i}" for i in range(10)]


def pre_deployment_checklist(checks: Dict[str, bool]) -> str:
    bot = DipHunterBot(
        market_data=MockMarketData(),
        execution=MockExecutionBackend(),
        risk_controller=MockRiskController(),
    )
    return bot.pre_deployment_checklist(checks)


def deploy_with_gradual_scaling() -> List[str]:
    bot = DipHunterBot(
        market_data=MockMarketData(),
        execution=MockExecutionBackend(),
        risk_controller=MockRiskController(),
    )

    def update_trading_limits(stage: Dict[str, int]) -> None:
        return None

    def evaluate_stage_performance() -> Dict[str, int]:
        return {"issues": 0}

    def sleep(seconds: int) -> None:
        return None

    return bot.deploy_with_gradual_scaling(update_trading_limits, evaluate_stage_performance, sleep)


# ----------------------------------------------------------------------
# Mock dependencies for documentation/testing convenience
# ----------------------------------------------------------------------


class MockMarketData(MarketDataProvider):
    def list_top_pairs(self, count: int) -> Sequence[str]:
        return [f"COIN{i}" for i in range(count)]

    def get_price_change(self, pair: str, timeframe: str) -> float:
        return -5.0

    def get_volume(self, pair: str, timeframe: str) -> float:
        return 1_500

    def get_average_volume(self, pair: str, timeframe: str, periods: int) -> float:
        return 800

    def get_rsi(self, pair: str, timeframe: str) -> float:
        return 25

    def get_price(self, pair: str) -> float:
        return 100.0

    def get_bollinger_lower(self, pair: str, timeframe: str) -> float:
        return 98.0

    def get_support_distance(self, pair: str, price: float) -> float:
        return 0.02

    def get_macd_divergence(self, pair: str) -> bool:
        return True


class MockExecutionBackend(ExecutionBackend):
    def __init__(self) -> None:
        self.orders: List[Order] = []

    def place_limit_order(self, order: Order) -> str:
        self.orders.append(order)
        return "ORDER123"

    def place_take_profit_order(self, order: Order) -> None:
        self.orders.append(order)

    def place_stop_loss_order(self, order: Order) -> None:
        self.orders.append(order)

    def execute_scaled_orders(self, base_order: Order, portions: int) -> None:
        for _ in range(portions):
            self.orders.append(base_order)

    def queue_for_batching(self, order: Order) -> None:
        self.orders.append(order)


class MockRiskController(RiskController):
    def validate_risk_parameters(self) -> bool:
        return True
