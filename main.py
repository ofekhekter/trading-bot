from datetime import datetime
import threading
import time

from risk_manager import RiskManager
from decision_engine import DecisionEngine
from technical_analysis import TechnicalAnalyzer
from news_analyzer import NewsAnalyzer
from ib_market_data import get_historical_bars
from ib_news_test import get_recent_news
from ib_connection import IBConnection, run_loop
from order_executor import OrderExecutor


BOT_NAME = "IBKR Trading Bot"

WATCHLIST = [
    "NVDA",
    "AMD",
    "AVGO",
    "PLTR",
    "MSFT",
    "AAPL",
]

MAX_CAPITAL_USD = 6000.00
MAX_POSITION_USD = 2000.00
TRADE_AMOUNT_USD = 1000.00

# KEEP FALSE UNTIL WE APPROVE THE DRY RUN
PAPER_EXECUTION_ENABLED = False


risk = RiskManager(
    max_capital=MAX_CAPITAL_USD,
    max_position=MAX_POSITION_USD,
)

decision_engine = DecisionEngine()
technical_analyzer = TechnicalAnalyzer()
news_analyzer = NewsAnalyzer()


print("=" * 60)
print(BOT_NAME)
print("=" * 60)
print(f"Started: {datetime.now()}")
print(f"Watchlist: {', '.join(WATCHLIST)}")
print(f"Trade amount: ${TRADE_AMOUNT_USD:,.2f}")
print(f"Paper execution enabled: {PAPER_EXECUTION_ENABLED}")

if PAPER_EXECUTION_ENABLED:
    print("IBKR PAPER ORDER EXECUTION ENABLED")
else:
    print("DRY RUN MODE - NO ORDERS WILL BE SENT")


candidates = []


for symbol in WATCHLIST:

    print("\n" + "=" * 60)
    print(f"SCANNING: {symbol}")
    print("=" * 60)

    # --------------------------------------------------
    # MARKET DATA
    # --------------------------------------------------

    try:
        bars = get_historical_bars(
            symbol=symbol,
            duration="2 D",
            bar_size="5 mins",
        )
    except Exception as exc:
        print(f"{symbol}: market data error: {exc}")
        continue

    if not bars:
        print(f"{symbol}: no market data received.")
        continue

    real_prices = [
        bar["close"]
        for bar in bars
    ]

    technical_result = technical_analyzer.calculate_score(
        real_prices
    )

    print(
        f"Price: ${technical_result['current_price']}"
    )
    print(
        f"EMA20: {technical_result['ema20']}"
    )
    print(
        f"EMA50: {technical_result['ema50']}"
    )
    print(
        f"RSI14: {technical_result['rsi14']}"
    )
    print(
        f"Momentum: "
        f"{technical_result['momentum_percent']}%"
    )
    print(
        f"Technical score: "
        f"{technical_result['technical_score']}/100"
    )

    # --------------------------------------------------
    # NEWS
    # --------------------------------------------------

    try:
        news_items = get_recent_news(symbol)
    except Exception as exc:
        print(f"{symbol}: news error: {exc}")
        news_items = []

    headlines = [
        item["headline"]
        for item in news_items
    ]

    news_result = news_analyzer.analyze_headlines(
        headlines,
        current_price=technical_result["current_price"],
    )

    if news_result is None:
        news_result = {
            "news_score": 0.0,
            "has_critical_news": False,
            "critical_headlines": [],
            "highest_price_target": None,
            "target_upside_percent": None,
            "target_bonus": 0.0,
        }

    print(
        f"News articles: {len(news_items)}"
    )
    print(
        f"News score: {news_result['news_score']}"
    )

    # --------------------------------------------------
    # DECISION ENGINE
    # --------------------------------------------------

    result = decision_engine.evaluate(
        symbol=symbol,

        # Temporary neutral fundamental score.
        # We will replace this later with real fundamentals.
        fundamental_score=50,

        technical_score=technical_result[
            "technical_score"
        ],
        news_score=news_result["news_score"],
        has_critical_news=news_result[
            "has_critical_news"
        ],
        earnings_soon=False,
        rsi=technical_result["rsi14"],
        momentum=technical_result[
            "momentum_percent"
        ],
        price=technical_result[
            "current_price"
        ],
        ema20=technical_result["ema20"],
        ema50=technical_result["ema50"],
    )

    print("\nDecision:")
    print(f"Action: {result['action']}")
    print(
        f"Entry action: "
        f"{result['entry_action']}"
    )
    print(
        f"Confidence: "
        f"{result['confidence']}"
    )
    print(
        f"Long score: "
        f"{result['long_score']}"
    )
    print(
        f"Short score: "
        f"{result['short_score']}"
    )
    print(
        f"Score gap: "
        f"{result['score_gap']}"
    )

    if result["entry_reasons"]:
        print("Entry reasons:")

        for reason in result["entry_reasons"]:
            print(f"  - {reason}")

    # --------------------------------------------------
    # SAVE VALID CANDIDATES
    # --------------------------------------------------

    if result["entry_action"] in (
        "ENTER_LONG",
        "ENTER_SHORT",
    ):

        candidates.append(
            {
                "symbol": symbol,
                "result": result,
                "technical": technical_result,
                "news": news_result,
            }
        )

        print(
            f">>> {symbol} ADDED AS TRADE CANDIDATE"
        )

    else:
        print(
            f"{symbol}: no entry right now."
        )


# ======================================================
# SELECT BEST CANDIDATE
# ======================================================

print("\n" + "=" * 60)
print("SCAN COMPLETE")
print("=" * 60)

if not candidates:
    print("No valid trade candidates found.")
    print("No order will be sent.")
    raise SystemExit


candidates.sort(
    key=lambda item: item["result"]["confidence"],
    reverse=True,
)

best = candidates[0]

symbol = best["symbol"]
result = best["result"]
technical_result = best["technical"]


print("\nBEST CANDIDATE")
print(f"Symbol: {symbol}")
print(
    f"Entry action: "
    f"{result['entry_action']}"
)
print(
    f"Confidence: "
    f"{result['confidence']}"
)


# ======================================================
# RISK MANAGER
# ======================================================

trade_direction = (
    "LONG"
    if result["entry_action"] == "ENTER_LONG"
    else "SHORT"
)

trade_plan = risk.calculate_trade_plan(
    action=trade_direction,
    price=technical_result["current_price"],
    trade_amount=TRADE_AMOUNT_USD,
)

if not trade_plan["approved"]:
    print("\nTRADE BLOCKED BY RISK MANAGER")
    print(trade_plan["reason"])
    raise SystemExit


print("\n--- TRADE EXECUTION PLAN ---")

print(f"Symbol: {symbol}")
print(f"Direction: {trade_direction}")
print(
    f"Order action: "
    f"{trade_plan['order_action']}"
)
print(
    f"Quantity: "
    f"{trade_plan['quantity']}"
)
print(
    f"Estimated entry: "
    f"${trade_plan['entry_price']}"
)
print(
    f"Position value: "
    f"${trade_plan['position_value']}"
)
print(
    f"Stop Loss: "
    f"${trade_plan['stop_price']}"
)
print(
    f"Take Profit: "
    f"${trade_plan['take_profit_price']}"
)


# ======================================================
# DRY RUN SAFETY STOP
# ======================================================

if not PAPER_EXECUTION_ENABLED:

    print("\nDRY RUN COMPLETE.")
    print("NO ORDER WAS SENT TO IBKR.")

    raise SystemExit


# ======================================================
# PAPER EXECUTION
# ======================================================

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
    print(
        "ORDER BLOCKED: "
        "Could not connect to IBKR."
    )

    ib_app.disconnect()

    raise SystemExit


start_time = time.time()

while (
    not ib_app.managed_accounts
    and time.time() - start_time < timeout
):
    time.sleep(0.1)


if not ib_app.managed_accounts:
    print(
        "ORDER BLOCKED: "
        "No IBKR account detected."
    )

    ib_app.disconnect()

    raise SystemExit


account = ib_app.managed_accounts[0]


# ABSOLUTE PAPER ACCOUNT BLOCK
if not account.upper().startswith("DU"):

    print(
        "ORDER BLOCKED: "
        "ACCOUNT IS NOT PAPER."
    )

    ib_app.disconnect()

    raise SystemExit


print("PAPER ACCOUNT VERIFIED.")


executor = OrderExecutor(
    ib_app
)


executor.place_bracket_order(
    symbol=symbol,
    action=trade_plan["order_action"],
    quantity=trade_plan["quantity"],
    stop_price=trade_plan["stop_price"],
    take_profit_price=trade_plan[
        "take_profit_price"
    ],
)


time.sleep(5)

ib_app.disconnect()

print("\nPAPER ORDER PROCESS FINISHED.")