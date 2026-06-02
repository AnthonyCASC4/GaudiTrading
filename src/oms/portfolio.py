"""Paper trading portfolio — tracks positions, P&L, and trade history."""

import time
from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity

    @property
    def pnl_percent(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return ((self.current_price - self.avg_cost) / self.avg_cost) * 100


@dataclass
class Trade:
    id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: float
    total: float = 0.0

    def __post_init__(self):
        self.total = self.quantity * self.price


@dataclass
class Portfolio:
    """Paper trading portfolio with $10,000 starting balance."""

    starting_cash: float = 10_000.0
    cash: float = 10_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)

    @property
    def total_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    @property
    def total_return(self) -> float:
        return self.total_value - self.starting_cash

    @property
    def total_return_percent(self) -> float:
        return (self.total_return / self.starting_cash) * 100

    def update_prices(self, symbol: str, price: float):
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    def buy(self, symbol: str, quantity: float, price: float) -> Trade | str:
        cost = quantity * price
        if cost > self.cash:
            max_qty = self.cash / price
            return f"Not enough cash. You have ${self.cash:,.2f} which can buy {max_qty:.4f} {symbol}."

        self.cash -= cost

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, current_price=price)

        pos = self.positions[symbol]
        # Update average cost
        total_qty = pos.quantity + quantity
        if total_qty > 0:
            pos.avg_cost = (pos.avg_cost * pos.quantity + price * quantity) / total_qty
        pos.quantity = total_qty
        pos.current_price = price

        trade = Trade(
            id=f"T{len(self.trades)+1:04d}",
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            timestamp=time.time(),
        )
        self.trades.append(trade)
        return trade

    def sell(self, symbol: str, quantity: float, price: float) -> Trade | str:
        pos = self.positions.get(symbol)
        if not pos or pos.quantity < quantity:
            held = pos.quantity if pos else 0
            return f"You only hold {held:.4f} {symbol}."

        self.cash += quantity * price
        pos.quantity -= quantity
        pos.current_price = price

        if pos.quantity == 0:
            del self.positions[symbol]

        trade = Trade(
            id=f"T{len(self.trades)+1:04d}",
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price,
            timestamp=time.time(),
        )
        self.trades.append(trade)
        return trade

    def to_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "total_value": round(self.total_value, 2),
            "total_return": round(self.total_return, 2),
            "total_return_percent": round(self.total_return_percent, 2),
            "positions": {
                sym: {
                    "quantity": round(p.quantity, 6),
                    "avg_cost": round(p.avg_cost, 2),
                    "current_price": round(p.current_price, 2),
                    "market_value": round(p.market_value, 2),
                    "unrealized_pnl": round(p.unrealized_pnl, 2),
                    "pnl_percent": round(p.pnl_percent, 2),
                }
                for sym, p in self.positions.items()
            },
            "trade_count": len(self.trades),
            "recent_trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "quantity": round(t.quantity, 6),
                    "price": round(t.price, 2),
                    "total": round(t.total, 2),
                    "timestamp": t.timestamp,
                }
                for t in self.trades[-20:]
            ],
        }
