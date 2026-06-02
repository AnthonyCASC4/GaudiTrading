"""FastAPI server — educational investing platform backend."""

import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.market_data.feed import MarketDataFeed, ETF_INFO, HISTORICAL_RETURNS
from src.oms.portfolio import Portfolio
from src.analytics.ai_analyst import AIMarketAnalyst
from src.analytics.retirement import (
    project_retirement,
    compare_scenarios,
    savings_account_comparison,
)
from src.monitor.metrics import SystemMonitor

app = FastAPI(title="GaudiTrading", version="0.2.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Core components
feed = MarketDataFeed()
portfolio = Portfolio(starting_cash=10_000.0)
monitor = SystemMonitor()
analyst = AIMarketAnalyst(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    analysis_interval=int(os.environ.get("ANALYSIS_INTERVAL", "120")),
)
analyst.attach(feed, None)

ws_clients: set[WebSocket] = set()


async def on_quote(quote):
    """Forward quotes to portfolio and dashboard."""
    portfolio.update_prices(quote.symbol, quote.price)
    msg = json.dumps({
        "type": "quote",
        "symbol": quote.symbol,
        "price": quote.price,
        "change": round(quote.change, 2),
        "change_percent": round(quote.change_percent, 2),
        "volume": quote.volume,
        "day_high": quote.day_high,
        "day_low": quote.day_low,
    })
    await _broadcast(msg)


async def _broadcast(msg: str):
    dead = set()
    for client in ws_clients:
        try:
            await client.send_text(msg)
        except Exception:
            dead.add(client)
    for d in dead:
        ws_clients.discard(d)


feed.subscribe(on_quote)


@app.on_event("startup")
async def startup():
    asyncio.create_task(feed.start())
    asyncio.create_task(analyst.start())
    print("[GaudiTrading] Platform online — your future starts here.")


@app.on_event("shutdown")
async def shutdown():
    await feed.stop()
    await analyst.stop()


# --- Pages ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open(os.path.join(TEMPLATES_DIR, "dashboard.html")) as f:
        return HTMLResponse(f.read())


# --- Market Data API ---

@app.get("/api/status")
async def system_status():
    return {
        "etfs": {
            sym: {
                **ETF_INFO[sym],
                "price": feed.get_price(sym),
                "historical_return": HISTORICAL_RETURNS.get(sym, 0),
                **(feed.stats.get(sym, {})),
            }
            for sym in feed.symbols
        },
        "portfolio": portfolio.to_dict(),
        "monitor": monitor.get_dashboard_snapshot(),
    }


@app.get("/api/etfs")
async def get_etfs():
    return {
        sym: {
            **ETF_INFO[sym],
            "price": feed.get_price(sym),
            "historical_annual_return": f"{HISTORICAL_RETURNS.get(sym, 0)*100:.1f}%",
            **(feed.stats.get(sym, {})),
        }
        for sym in feed.symbols
    }


# --- Portfolio API ---

@app.get("/api/portfolio")
async def get_portfolio():
    return portfolio.to_dict()


@app.post("/api/trade")
async def execute_trade(payload: dict):
    symbol = payload.get("symbol", "")
    side = payload.get("side", "")
    amount_dollars = float(payload.get("amount", 0))  # trade by dollar amount

    price = feed.get_price(symbol)
    if price <= 0:
        return {"error": f"No price available for {symbol} yet. Wait a moment for data to load."}

    # Convert dollar amount to shares (fractional shares allowed)
    quantity = amount_dollars / price

    if side == "buy":
        result = portfolio.buy(symbol, quantity, price)
    elif side == "sell":
        result = portfolio.sell(symbol, quantity, price)
    else:
        return {"error": "Side must be 'buy' or 'sell'"}

    if isinstance(result, str):
        return {"error": result}

    await _broadcast(json.dumps({
        "type": "trade",
        "portfolio": portfolio.to_dict(),
    }))

    return {
        "success": True,
        "trade": {
            "id": result.id,
            "symbol": result.symbol,
            "side": result.side,
            "quantity": round(result.quantity, 6),
            "price": round(result.price, 2),
            "total": round(result.total, 2),
        },
        "portfolio": portfolio.to_dict(),
    }


# --- Retirement Projections API ---

@app.post("/api/retirement/project")
async def retirement_project(payload: dict):
    proj = project_retirement(
        monthly_contribution=float(payload.get("monthly", 200)),
        annual_return=float(payload.get("annual_return", 0.10)),
        years=int(payload.get("years", 30)),
        starting_age=int(payload.get("starting_age", 25)),
        starting_balance=float(payload.get("starting_balance", 0)),
    )
    return {
        "monthly_contribution": proj.monthly_contribution,
        "years": proj.years,
        "starting_age": proj.starting_age,
        "retirement_age": proj.starting_age + proj.years,
        "final_value": proj.final_value,
        "total_contributed": proj.total_contributed,
        "total_growth": proj.total_growth,
        "monthly_retirement_income": proj.monthly_retirement_income,
        "ss_monthly": proj.ss_monthly,
        "combined_monthly": proj.combined_monthly,
        "gap_without_investing": proj.gap_without_investing,
        "snapshots": [
            {
                "year": s.year,
                "age": s.age,
                "contributed": s.total_contributed,
                "value": s.portfolio_value,
                "growth": s.growth_earned,
            }
            for s in proj.snapshots
        ],
    }


@app.get("/api/retirement/compare")
async def retirement_compare(
    starting_age: int = 25,
    annual_return: float = 0.10,
):
    return compare_scenarios(
        starting_age=starting_age,
        annual_return=annual_return,
    )


@app.get("/api/retirement/savings-vs-investing")
async def savings_vs_investing(
    monthly: float = 200,
    years: int = 30,
):
    return savings_account_comparison(
        monthly_contribution=monthly,
        years=years,
    )


# --- AI Coach API ---

@app.post("/api/ai/ask")
async def ai_ask(payload: dict):
    question = payload.get("question", "")
    if not question:
        return {"error": "No question provided"}
    if not analyst.api_key:
        return {"error": "AI coach is not configured. Set ANTHROPIC_API_KEY to enable."}
    answer = await analyst.analyze_on_demand(question)
    return {"answer": answer}


@app.get("/api/ai/analyses")
async def ai_analyses():
    return [
        {
            "summary": a.summary,
            "risk_level": a.risk_level,
            "signals": a.signals,
            "timestamp": a.timestamp,
        }
        for a in analyst.recent_analyses
    ]


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)
