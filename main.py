from datetime import datetime
from risk_manager import RiskManager
from decision_engine import DecisionEngine
from technical_analysis import TechnicalAnalyzer
from news_analyzer import NewsAnalyzer
from ib_market_data import get_historical_bars
from ib_news_test import get_recent_news
import threading
import time

from ib_connection import IBConnection, run_loop
from order_executor import OrderExecutor

BOT_NAME = "IBKR Trading Bot"

MAX_CAPITAL_USD = 6000.00
MAX_POSITION_USD = 2000.00
PAPER_EXECUTION_ENABLED = False
TRADE_AMOUNT_USD = 1000.00

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
print(f"Paper execution enabled: {PAPER_EXECUTION_ENABLED}")

if PAPER_EXECUTION_ENABLED:
    print("IBKR PAPER ORDER EXECUTION ENABLED")
else:
    print("DRY RUN MODE - NO ORDERS WILL BE SENT")

print("\n--- MULTIPLE TRADES RISK TEST ---")



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

print("\n--- TRADE EXECUTION PLAN ---")

entry_action = result["entry_action"]

if entry_action not in ("ENTER_LONG", "ENTER_SHORT"):
    print(f"No trade will be opened.")
    print(f"Entry action: {entry_action}")
    raise SystemExit

trade_direction = (
    "LONG"
    if entry_action == "ENTER_LONG"
    else "SHORT"
)

current_price = technical_result["current_price"]

trade_plan = risk.calculate_trade_plan(
    action=trade_direction,
    price=current_price,
    trade_amount=TRADE_AMOUNT_USD,
)

if not trade_plan["approved"]:
    print("TRADE BLOCKED BY RISK MANAGER")
    print(trade_plan["reason"])
    raise SystemExit

print(f"Direction: {trade_direction}")
print(f"Order action: {trade_plan['order_action']}")
print(f"Quantity: {trade_plan['quantity']}")
print(f"Estimated entry: ${trade_plan['entry_price']}")
print(f"Position value: ${trade_plan['position_value']}")
print(f"Stop Loss: ${trade_plan['stop_price']}")
print(f"Take Profit: ${trade_plan['take_profit_price']}")

if not PAPER_EXECUTION_ENABLED:
    print("\nDRY RUN COMPLETE.")
    print("NO ORDER WAS SENT TO IBKR.")
    raise SystemExit


print("\n--- CONNECTING FOR PAPER EXECUTION ---")

ib_app = IBConnection()

ib_app.connect(
    "127.0.0.1",
    7497,
    clientId=10,
)

api_thread = threading.Thread(
    target=run_loop,
    args=(ib_app,),
    daemon=True,
)

api_thread.start()

timeout = 10
start_time = time.time()

while (
    not ib_app.connected_successfully
    and time.time() - start_time < timeout
):
    time.sleep(0.1)

if not ib_app.connected_successfully:
    print("ORDER BLOCKED: Could not connect to IBKR.")
    ib_app.disconnect()
    raise SystemExit

start_time = time.time()

while (
    not ib_app.managed_accounts
    and time.time() - start_time < timeout
):
    time.sleep(0.1)

if not ib_app.managed_accounts:
    print("ORDER BLOCKED: No IBKR account detected.")
    ib_app.disconnect()
    raise SystemExit

account = ib_app.managed_accounts[0]

if not account.upper().startswith("DU"):
    print("ORDER BLOCKED: ACCOUNT IS NOT PAPER.")
    ib_app.disconnect()
    raise SystemExit

print("PAPER ACCOUNT VERIFIED.")

executor = OrderExecutor(ib_app)

executor.place_bracket_order(
    symbol=result["symbol"],
    action=trade_plan["order_action"],
    quantity=trade_plan["quantity"],
    stop_price=trade_plan["stop_price"],
    take_profit_price=trade_plan["take_profit_price"],
)

time.sleep(5)

ib_app.disconnect()

print("\nPAPER ORDER PROCESS FINISHED.")