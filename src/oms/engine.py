"""Order Management System — simulates order lifecycle with latency tracking."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    NEW = "new"
    VALIDATED = "validated"
    ROUTED = "routed"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class OrderEvent:
    order_id: str
    status: OrderStatus
    timestamp_ns: int
    details: str = ""


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None  # None for market orders
    status: OrderStatus = OrderStatus.NEW
    created_at_ns: int = 0
    events: list[OrderEvent] = field(default_factory=list)
    fill_price: float = 0.0
    latency_breakdown_us: dict = field(default_factory=dict)

    @property
    def total_latency_us(self) -> float:
        return sum(self.latency_breakdown_us.values())


@dataclass
class OrderManagementSystem:
    """Simulates the order lifecycle: new → validated → routed → filled/rejected."""

    orders: dict[str, Order] = field(default_factory=dict)
    _event_log: deque = field(default_factory=lambda: deque(maxlen=200), repr=False)
    _subscribers: list = field(default_factory=list, repr=False)
    _last_prices: dict[str, float] = field(default_factory=dict, repr=False)

    # Simulated latency ranges (microseconds)
    VALIDATION_LATENCY = (50, 200)
    ROUTING_LATENCY = (100, 500)
    MATCHING_LATENCY = (20, 150)

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def update_price(self, symbol: str, price: float):
        self._last_prices[symbol] = price

    @property
    def event_log(self) -> list[OrderEvent]:
        return list(self._event_log)

    @property
    def recent_orders(self) -> list[Order]:
        return list(self.orders.values())[-50:]

    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ) -> Order:
        import random

        order_id = str(uuid.uuid4())[:8]
        now = time.time_ns()
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            created_at_ns=now,
        )
        self.orders[order_id] = order
        self._log_event(order, OrderStatus.NEW, "Order received")

        # Stage 1: Validation
        await asyncio.sleep(random.uniform(*self.VALIDATION_LATENCY) / 1e6)
        validation_time = (time.time_ns() - now) / 1000
        order.latency_breakdown_us["validation"] = validation_time

        # Reject invalid orders
        if quantity <= 0 or (order_type == OrderType.LIMIT and price is None):
            order.status = OrderStatus.REJECTED
            self._log_event(order, OrderStatus.REJECTED, "Failed validation")
            await self._notify(order)
            return order

        order.status = OrderStatus.VALIDATED
        self._log_event(order, OrderStatus.VALIDATED, "Passed risk checks")

        # Stage 2: Routing
        route_start = time.time_ns()
        await asyncio.sleep(random.uniform(*self.ROUTING_LATENCY) / 1e6)
        order.latency_breakdown_us["routing"] = (time.time_ns() - route_start) / 1000
        order.status = OrderStatus.ROUTED
        self._log_event(order, OrderStatus.ROUTED, "Routed to matching engine")

        # Stage 3: Matching
        match_start = time.time_ns()
        await asyncio.sleep(random.uniform(*self.MATCHING_LATENCY) / 1e6)
        order.latency_breakdown_us["matching"] = (time.time_ns() - match_start) / 1000

        # Simulate fill using last known price
        last_price = self._last_prices.get(symbol, 0)
        if last_price > 0:
            slippage = random.uniform(-0.0001, 0.0001)
            order.fill_price = last_price * (1 + slippage)

            if order_type == OrderType.LIMIT and price is not None:
                if (side == OrderSide.BUY and order.fill_price > price) or (
                    side == OrderSide.SELL and order.fill_price < price
                ):
                    order.status = OrderStatus.REJECTED
                    self._log_event(order, OrderStatus.REJECTED, "Price moved past limit")
                    await self._notify(order)
                    return order

            order.status = OrderStatus.FILLED
            self._log_event(
                order,
                OrderStatus.FILLED,
                f"Filled @ ${order.fill_price:,.2f} | total latency: {order.total_latency_us:.0f}μs",
            )
        else:
            order.status = OrderStatus.REJECTED
            self._log_event(order, OrderStatus.REJECTED, "No market price available")

        await self._notify(order)
        return order

    def _log_event(self, order: Order, status: OrderStatus, details: str):
        event = OrderEvent(
            order_id=order.id,
            status=status,
            timestamp_ns=time.time_ns(),
            details=details,
        )
        order.events.append(event)
        self._event_log.append(event)

    async def _notify(self, order: Order):
        for cb in self._subscribers:
            try:
                await cb(order)
            except Exception as e:
                print(f"[OMS] Subscriber error: {e}")

    def get_stats(self) -> dict:
        filled = [o for o in self.orders.values() if o.status == OrderStatus.FILLED]
        rejected = [o for o in self.orders.values() if o.status == OrderStatus.REJECTED]
        latencies = [o.total_latency_us for o in filled]
        sorted_lats = sorted(latencies) if latencies else [0]
        n = len(sorted_lats)
        return {
            "total_orders": len(self.orders),
            "filled": len(filled),
            "rejected": len(rejected),
            "avg_latency_us": sum(latencies) / n if n else 0,
            "p50_latency_us": sorted_lats[int(n * 0.50)] if n else 0,
            "p99_latency_us": sorted_lats[min(int(n * 0.99), n - 1)] if n else 0,
        }
