from datetime import datetime
from risk_manager import RiskManager
from decision_engine import DecisionEngine
from technical_analysis import TechnicalAnalyzer
from news_analyzer import NewsAnalyzer
from ib_market_data import get_historical_bars
from ib_news_test import get_recent_news

BOT_NAME = "IBKR Trading Bot"

MAX_CAPITAL_USD = 6000.00
MAX_POSITION_USD = 2000.00
LIVE_TRADING = False

risk = RiskManager(
    max_capital=MAX_CAPITAL_USD,
    max_position=MAX_POSITION_USD
)

decision_engine = DecisionEngine()
technical_analyzer = TechnicalAnalyzer()
news_analyzer = NewsAnalyzer()

print("=" * 45)
print(BOT_NAME)
print("=" * 45)
print(f"Started: {datetime.now()}")
print(f"Maximum capital: ${MAX_CAPITAL_USD:,.2f}")
print(f"Maximum position: ${MAX_POSITION_USD:,.2f}")
print(f"Live trading: {LIVE_TRADING}")

if LIVE_TRADING:
    print("WARNING: LIVE TRADING ENABLED")
else:
    print("SAFE MODE: PAPER TRADING ONLY")

print("\n--- MULTIPLE TRADES RISK TEST ---")

trades = [
    ("NVDA", 1800.00),
    ("AMD", 1500.00),
    ("AVGO", 1900.00),
    ("PLTR", 1200.00),
]

for symbol, amount in trades:
    print(f"\n{symbol}: requesting ${amount:,.2f}")

    approved, reason = risk.can_open_position(amount)
    print(reason)

    if approved:
        risk.register_position(amount)
        print(f"{symbol}: APPROVED")
    else:
        print(f"{symbol}: BLOCKED")

    print(
        f"Capital: ${risk.used_capital:,.2f} "
        f"/ ${MAX_CAPITAL_USD:,.2f}"
    )

print("\n--- TECHNICAL ANALYSIS TEST ---")

print("\n--- REAL MARKET DATA ---")

bars = get_historical_bars(
    symbol="NVDA",
    duration="2 D",
    bar_size="5 mins"
)

if not bars:
    print("No market data received from IBKR.")
    raise SystemExit

real_prices = [
    bar["close"]
    for bar in bars
]

technical_result = technical_analyzer.calculate_score(
    real_prices
)

print(f"Bars received: {len(bars)}")
print(f"Current price: ${technical_result['current_price']}")
print(f"EMA20: {technical_result['ema20']}")
print(f"EMA50: {technical_result['ema50']}")
print(f"RSI14: {technical_result['rsi14']}")
print(f"Momentum: {technical_result['momentum_percent']}%")
print(f"Technical score: {technical_result['technical_score']}/100")

technical_result = technical_analyzer.calculate_score(
    real_prices
)

print(f"Current price: "f"${technical_result['current_price']}")

print("\n--- REAL NEWS ANALYSIS ---")

news_items = get_recent_news("NVDA")

headlines = [
    item["headline"]
    for item in news_items
]

news_result = news_analyzer.analyze_headlines(
    headlines,
    current_price=technical_result["current_price"]
)

print(f"News articles found: {len(news_items)}")

for item in news_items:
    cleaned_headline = news_analyzer.clean_headline(
        item["headline"]
    )

    print(f"- [{item['provider']}] "f"{cleaned_headline}")

if news_result is None:
    news_result = {
        "news_score": 0.0,
        "has_critical_news": False,
        "critical_headlines": [],
        "highest_price_target": None,
        "target_upside_percent": None,
        "target_bonus": 0.0,
    }
    
print(f"News score: {news_result['news_score']}")
print(f"Highest price target: ${news_result['highest_price_target']}")
print(f"Target upside: {news_result['target_upside_percent']}%")
print(f"Target bonus: {news_result['target_bonus']}")
print(f"Critical news: "f"{news_result['has_critical_news']}")

print("\n--- FINAL DECISION TEST ---")

result = decision_engine.evaluate(
    symbol="NVDA",
    fundamental_score=82,
    technical_score=technical_result["technical_score"],
    news_score=news_result["news_score"],
    has_critical_news=news_result["has_critical_news"],
    earnings_soon=False,
    rsi=technical_result["rsi14"],
    momentum=technical_result["momentum_percent"],
    price=technical_result["current_price"],
    ema20=technical_result["ema20"],
    ema50=technical_result["ema50"],
)

print(f"Symbol: {result['symbol']}")
print(f"Technical score used: {technical_result['technical_score']}")
print(f"Action: {result['action']}")
print(f"Confidence: {result['confidence']}")
print(f"Long score: {result['long_score']}")
print(f"Short score: {result['short_score']}")
print(f"Score gap: {result['score_gap']}")
print(f"Long evidence count: {result['long_evidence_count']}")
print(f"Short evidence count: {result['short_evidence_count']}")
print(f"Entry action: {result['entry_action']}")
print("Entry reasons:")
for reason in result["entry_reasons"]:
    print(f"  - {reason}")
print("Long reasons:")
for reason in result["long_reasons"]:
    print(f"  - {reason}")

print("Short reasons:")
for reason in result["short_reasons"]:
    print(f"  - {reason}")

print(
    f"EMA20: "
    f"{technical_result['ema20']}"
)

print(
    f"EMA50: "
    f"{technical_result['ema50']}"
)

print(
    f"RSI14: "
    f"{technical_result['rsi14']}"
)

print(
    f"Momentum: "
    f"{technical_result['momentum_percent']}%"
)

print(
    f"Technical score: "
    f"{technical_result['technical_score']}"
)

print(f"Final score: {result['final_score']}")