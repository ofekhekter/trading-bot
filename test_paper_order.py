import threading
import time

from ib_connection import IBConnection
from order_executor import OrderExecutor
from risk_manager import RiskManager


def run_loop(app):
    app.run()


app = IBConnection()

print("Connecting to TWS...")

app.connect(
    "127.0.0.1",
    7497,
    clientId=2,
)

api_thread = threading.Thread(
    target=run_loop,
    args=(app,),
    daemon=True,
)

api_thread.start()

# Wait for connection + managed account
for _ in range(20):

    if (
        app.connected_successfully
        and app.next_order_id is not None
        and app.managed_accounts
    ):
        break

    time.sleep(0.5)

if not app.connected_successfully:
    raise RuntimeError(
        "Failed to connect to IBKR."
    )

if not app.managed_accounts:
    raise RuntimeError(
        "No managed account received."
    )

account = app.managed_accounts[0]

if not account.upper().startswith("DU"):
    raise RuntimeError(
        "ORDER BLOCKED: Not a PAPER account."
    )

print(
    f"Detected PAPER account: "
    f"{account[:2]}..."
)

# ==========================================
# TEST SETTINGS
# ==========================================

symbol = "AAPL"

# Temporary reference price only.
# We will replace this later with market data.
reference_price = 325.00

# Slightly above one AAPL share
# so RiskManager calculates quantity = 1.
trade_amount = 330.00

# ==========================================
# RISK MANAGER
# ==========================================

risk_manager = RiskManager(
    max_capital=1000.00,
    max_position=500.00,
    stop_loss_pct=1.0,
    take_profit_pct=2.0,
)

trade_plan = (
    risk_manager.calculate_trade_plan(
        action="LONG",
        price=reference_price,
        trade_amount=trade_amount,
    )
)

if not trade_plan["approved"]:
    raise RuntimeError(
        trade_plan["reason"]
    )

# HARD TEST SAFETY:
# This test must NEVER send more than 1 share.
if trade_plan["quantity"] != 1:
    raise RuntimeError(
        f"TEST BLOCKED: Expected quantity 1, "
        f"got {trade_plan['quantity']}."
    )

print("=" * 60)
print("RISK MANAGER TRADE PLAN")
print("=" * 60)

print(
    f"Symbol: {symbol}"
)

print(
    f"Reference price: "
    f"{trade_plan['entry_price']:.2f}"
)

print(
    f"Quantity: "
    f"{trade_plan['quantity']}"
)

print(
    f"Stop Loss: "
    f"{trade_plan['stop_price']:.2f}"
)

print(
    f"Take Profit: "
    f"{trade_plan['take_profit_price']:.2f}"
)

print("=" * 60)

# ==========================================
# ORDER EXECUTION
# ==========================================

executor = OrderExecutor(app)

executor.place_bracket_order(
    symbol=symbol,
    action=trade_plan[
        "order_action"
    ],
    quantity=trade_plan[
        "quantity"
    ],
    stop_price=trade_plan[
        "stop_price"
    ],
    take_profit_price=trade_plan[
        "take_profit_price"
    ],
)

print(
    "Waiting for IBKR order updates..."
)

time.sleep(10)

print("=" * 60)
print("ORDER STATUS SNAPSHOT")

for order_id, data in (
    app.order_statuses.items()
):

    print(
        order_id,
        data
    )

print("=" * 60)

app.disconnect()

print("Disconnected.")