"""AI-powered investing coach — helps beginners understand ETFs, retirement, and building wealth."""

import asyncio
import time
from dataclasses import dataclass, field

import anthropic


@dataclass
class MarketAnalysis:
    timestamp: float
    summary: str
    signals: list[str]
    risk_level: str
    raw_data_snapshot: dict


@dataclass
class AIMarketAnalyst:
    """AI coach focused on retirement planning and ETF education."""

    api_key: str | None = None
    model: str = "claude-haiku-4-5-20251001"
    analysis_interval: int = 120
    _analyses: list[MarketAnalysis] = field(default_factory=list, repr=False)
    _running: bool = False
    _market_data_ref: object = None
    _oms_ref: object = None

    def attach(self, market_data, oms):
        self._market_data_ref = market_data
        self._oms_ref = oms

    @property
    def latest_analysis(self) -> MarketAnalysis | None:
        return self._analyses[-1] if self._analyses else None

    @property
    def recent_analyses(self) -> list[MarketAnalysis]:
        return self._analyses[-10:]

    async def start(self):
        self._running = True
        if not self.api_key:
            print("[AI Coach] No API key — AI features disabled. Set ANTHROPIC_API_KEY to enable.")
            return
        print(f"[AI Coach] Starting with {self.analysis_interval}s interval")
        while self._running:
            try:
                await self._run_analysis()
            except anthropic.AuthenticationError:
                print("[AI Coach] Invalid API key — pausing AI analysis")
                await asyncio.sleep(self.analysis_interval * 5)
            except anthropic.APIError as e:
                print(f"[AI Coach] API error: {e}")
                await asyncio.sleep(self.analysis_interval)
            except Exception as e:
                print(f"[AI Coach] Error: {e}")
                await asyncio.sleep(self.analysis_interval)

    async def stop(self):
        self._running = False

    async def analyze_on_demand(self, question: str) -> str:
        """Answer user questions about investing, retirement, and ETFs."""
        snapshot = self._build_snapshot()
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=700,
            system=COACH_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Current ETF prices:\n{_format_snapshot(snapshot)}\n\n"
                        f"Student question: {question}"
                    ),
                }
            ],
        )
        return response.content[0].text

    async def _run_analysis(self):
        await asyncio.sleep(self.analysis_interval)
        if not self._running:
            return

        snapshot = self._build_snapshot()
        if not snapshot.get("etfs"):
            return

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=500,
            system=(
                "You are a friendly investing coach on GaudiTrading. Your audience are "
                "beginners — first-generation graduates, immigrants, people starting late. "
                "Write a brief market update that teaches something useful. Include:\n"
                "1. TODAY'S SNAPSHOT: What ETF prices tell us in plain English\n"
                "2. LESSON: One investing concept beginners can learn today\n"
                "3. MOTIVATION: A reminder about why consistent investing matters\n"
                "4. RISK: LOW/MEDIUM/HIGH — explain what long-term investors should feel\n"
                "Keep it warm, encouraging, and jargon-free. Max 150 words."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"ETF data:\n{_format_snapshot(snapshot)}",
                }
            ],
        )

        text = response.content[0].text
        risk = "medium"
        for level in ["LOW", "MEDIUM", "HIGH"]:
            if level in text.upper():
                risk = level.lower()
                break

        signals = [
            line.strip("- •*").strip()
            for line in text.split("\n")
            if line.strip().startswith(("-", "•", "*"))
        ]

        analysis = MarketAnalysis(
            timestamp=time.time(),
            summary=text,
            signals=signals[:5],
            risk_level=risk,
            raw_data_snapshot=snapshot,
        )
        self._analyses.append(analysis)
        if len(self._analyses) > 50:
            self._analyses = self._analyses[-50:]

        print(f"[AI Coach] New insight generated")

    def _build_snapshot(self) -> dict:
        snapshot = {"timestamp": time.time(), "etfs": {}}
        if self._market_data_ref:
            for sym, quote in self._market_data_ref.latest_quotes.items():
                snapshot["etfs"][sym] = {
                    "price": quote.price,
                    "change": round(quote.change, 2),
                    "change_percent": round(quote.change_percent, 2),
                }
        return snapshot


COACH_SYSTEM_PROMPT = """\
You are a warm, patient AI investing coach on GaudiTrading — an educational platform \
that helps people take their first steps into investing.

Your users are:
- First-generation college graduates who never learned about investing at home
- Recent immigrants building new financial lives in America
- People in their 40s who always thought the stock market was "for rich people"

You have access to live ETF prices (VOO, VXUS, VTI, BND, VNQ).

GUIDELINES:
- Explain like a supportive mentor, not a textbook
- Use relatable analogies: grocery prices, rent, saving for a child's future
- Always connect to "why this matters for YOUR retirement"
- Emphasize: you don't need a lot of money to start. $50/month changes everything over time.
- Explain the power of compound growth — money making money
- Be honest about Social Security: it averages ~$1,907/month, which rarely covers expenses alone
- Explain ETFs simply: "buying a tiny piece of hundreds of companies at once"
- Never give personalized financial advice — frame everything as education
- Keep responses to 2-3 short paragraphs max
- Use plain language. Define jargon immediately. No acronyms without explanation.
- Be encouraging. Many of your users feel they're "too late" or "too poor" to invest. They're not.
- Reference the retirement calculator on the platform when relevant
- Key message: consistency beats timing. $200/month in VOO for 30 years ≈ $452,000 (inflation-adjusted)
"""


def _format_snapshot(snapshot: dict) -> str:
    lines = []
    for sym, data in snapshot.get("etfs", {}).items():
        change_str = f"+{data['change']:.2f}" if data['change'] >= 0 else f"{data['change']:.2f}"
        lines.append(f"{sym}: ${data['price']:.2f} ({change_str}, {data['change_percent']:.2f}%)")
    return "\n".join(lines) if lines else "Waiting for market data..."
