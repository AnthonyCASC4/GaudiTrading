# GaudiTrading — Your Future Starts Here

An educational investing platform that empowers people who've been left out of wealth-building to understand how consistent investing transforms retirement outcomes.

**Built for:** First-generation college graduates, recent immigrants, and anyone who thought the stock market "wasn't for people like me."

## The Problem

Social Security pays the average retiree **$1,907/month**. For most people, that's not enough to cover rent, groceries, and healthcare. But millions of Americans don't invest because they believe:
- "I don't have enough money to start"
- "It's too complicated"
- "It's too late for me"
- "The stock market is for rich people"

**None of that is true.** GaudiTrading shows people — with real numbers — how $50, $100, or $200/month invested consistently can change their future.

## What It Does

### Retirement Planner
- Interactive compound growth calculator with personalized projections
- **Social Security gap analysis** — shows exactly how much SS falls short and how investing fills the gap
- Visual growth charts showing contributed vs. market-earned money over 5/10/20/30 years
- Side-by-side comparison of different monthly amounts and timeframes
- All projections use real historical S&P 500 returns (~10% annual, inflation-adjusted)

### Practice Investing
- Paper trading with $10,000 play money — zero risk, real learning
- Live ETF prices (VOO, VXUS, VTI, BND, VNQ) from Yahoo Finance
- Fractional shares — buy $50 of VOO without needing to afford a full share
- Real-time portfolio tracking with P&L

### AI Trading Coach
- Powered by Claude AI — ask anything about investing in plain English
- Designed for beginners: uses analogies, avoids jargon, always encouraging
- Context-aware: has access to live market data and platform state
- Suggested questions for common beginner concerns

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Yahoo Finance  │────▶│  Market Data     │────▶│  System Monitor │
│  (ETF Prices)   │     │  Feed            │     │  (Metrics)      │
└─────────────────┘     └──────┬───────────┘     └─────────────────┘
                               │
                    ┌──────────▼───────────┐     ┌─────────────────┐
                    │  Paper Trading       │     │  Retirement     │
                    │  Portfolio Engine    │     │  Projections    │
                    └──────────┬───────────┘     └────────┬────────┘
                               │                          │
              ┌────────────────┼──────────────────────────┤
              ▼                ▼                           ▼
     ┌──────────────┐  ┌────────────┐            ┌──────────────┐
     │  AI Coach    │  │  FastAPI   │            │  WebSocket   │
     │  (Claude)    │  │  REST API  │            │  Live Feed   │
     └──────────────┘  └────────────┘            └──────┬───────┘
                                                        ▼
                                              ┌──────────────────┐
                                              │  Dashboard       │
                                              │  (3 tabs)        │
                                              └──────────────────┘
```

## Quick Start

```bash
pip install -e .

# Optional: enable AI Coach
export ANTHROPIC_API_KEY=your_key_here

uvicorn src.api.server:app --reload --port 8000
# Open http://localhost:8000
```

## Docker

```bash
ANTHROPIC_API_KEY=your_key docker compose up --build
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main dashboard |
| `/api/etfs` | GET | Current ETF prices + info |
| `/api/portfolio` | GET | Paper trading portfolio |
| `/api/trade` | POST | Execute a paper trade |
| `/api/retirement/project` | POST | Run a retirement projection |
| `/api/retirement/compare` | GET | Compare investment scenarios |
| `/api/retirement/savings-vs-investing` | GET | Bank savings vs. market investing |
| `/api/ai/ask` | POST | Ask the AI coach |
| `/ws` | WS | Live price updates |

## Technical Highlights

- **Async Python** — FastAPI + asyncio for non-blocking I/O across market data, AI, and WebSocket feeds
- **Real market data** — Live ETF prices from Yahoo Finance with periodic polling
- **AI integration** — Claude API with domain-specific system prompts for financial education
- **Compound growth engine** — Inflation-adjusted projections using historical return data (4% withdrawal rule)
- **WebSocket dashboard** — Real-time price updates pushed to connected clients
- **Containerized** — Docker + Docker Compose

## Tech Stack

Python 3.12 · FastAPI · asyncio · httpx · Anthropic Claude API · Pydantic · Docker
