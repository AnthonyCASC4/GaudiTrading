"""ETF market data feed — polls Yahoo Finance for real ETF prices."""

import asyncio
import time
from dataclasses import dataclass, field
from collections import deque

import httpx


# ETFs we track with educational context
ETF_INFO = {
    "VOO": {
        "name": "Vanguard S&P 500 ETF",
        "description": "Tracks the 500 largest US companies. When you buy VOO, you own a tiny piece of Apple, Microsoft, Amazon, and 497 other companies.",
        "category": "US Stocks",
    },
    "VXUS": {
        "name": "Vanguard Total International Stock ETF",
        "description": "Owns thousands of companies outside the US — Europe, Asia, emerging markets. Diversifies beyond America.",
        "category": "International Stocks",
    },
    "VTI": {
        "name": "Vanguard Total Stock Market ETF",
        "description": "Owns nearly every publicly traded US company — large, medium, and small. The broadest US stock fund.",
        "category": "US Stocks (Total)",
    },
    "BND": {
        "name": "Vanguard Total Bond Market ETF",
        "description": "Invests in US government and corporate bonds. Lower risk, steadier returns. Like lending money to reliable borrowers.",
        "category": "Bonds",
    },
    "VNQ": {
        "name": "Vanguard Real Estate ETF",
        "description": "Owns real estate companies — malls, apartments, offices. A way to invest in property without buying a house.",
        "category": "Real Estate",
    },
}

SYMBOLS = list(ETF_INFO.keys())

# Historical average annual returns (approximate, for projection calculations)
HISTORICAL_RETURNS = {
    "VOO": 0.1026,   # ~10.26% avg annual return (S&P 500 long-term)
    "VXUS": 0.065,   # ~6.5% international stocks
    "VTI": 0.10,     # ~10% total US market
    "BND": 0.04,     # ~4% bonds
    "VNQ": 0.09,     # ~9% real estate
}


@dataclass
class Quote:
    symbol: str
    price: float
    change: float
    change_percent: float
    previous_close: float
    day_high: float
    day_low: float
    volume: int
    timestamp: float


@dataclass
class MarketDataFeed:
    """Polls Yahoo Finance for real ETF prices."""

    symbols: list[str] = field(default_factory=lambda: SYMBOLS)
    poll_interval: int = 30  # seconds between polls
    _quotes: dict[str, Quote] = field(default_factory=dict, repr=False)
    _price_history: dict[str, deque] = field(default_factory=dict, repr=False)
    _subscribers: list = field(default_factory=list, repr=False)
    _running: bool = False

    def subscribe(self, callback):
        self._subscribers.append(callback)

    @property
    def latest_quotes(self) -> dict[str, Quote]:
        return dict(self._quotes)

    def get_price(self, symbol: str) -> float:
        q = self._quotes.get(symbol)
        return q.price if q else 0.0

    @property
    def stats(self) -> dict:
        return {
            sym: {"last_price": q.price, "change": q.change, "change_percent": q.change_percent}
            for sym, q in self._quotes.items()
        }

    async def start(self):
        self._running = True
        for sym in self.symbols:
            self._price_history[sym] = deque(maxlen=100)
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                print(f"[MarketData] Poll error: {e}")
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        self._running = False

    async def _poll(self):
        symbols_str = ",".join(self.symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_str}"
        headers = {"User-Agent": "Mozilla/5.0"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)
            data = resp.json()

        results = data.get("quoteResponse", {}).get("result", [])
        for item in results:
            symbol = item.get("symbol", "")
            if symbol not in self.symbols:
                continue

            quote = Quote(
                symbol=symbol,
                price=item.get("regularMarketPrice", 0),
                change=item.get("regularMarketChange", 0),
                change_percent=item.get("regularMarketChangePercent", 0),
                previous_close=item.get("regularMarketPreviousClose", 0),
                day_high=item.get("regularMarketDayHigh", 0),
                day_low=item.get("regularMarketDayLow", 0),
                volume=item.get("regularMarketVolume", 0),
                timestamp=time.time(),
            )
            self._quotes[symbol] = quote
            self._price_history[symbol].append(quote)

            for cb in self._subscribers:
                try:
                    await cb(quote)
                except Exception as e:
                    print(f"[MarketData] Subscriber error: {e}")

        if results:
            syms = [r.get("symbol") for r in results]
            prices = [f"{r.get('symbol')}=${r.get('regularMarketPrice', 0):.2f}" for r in results]
            print(f"[MarketData] Updated: {', '.join(prices)}")
