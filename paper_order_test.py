import threading
import time

from ib_connection import IBConnection, run_loop
from order_executor import OrderExecutor


TEST_SYMBOL = "AAPL"
TEST_QUANTITY = 1

# This is only an execution infrastructure test.
# It is NOT a strategy-generated trade.
TEST_STOP_PRICE = 312.86
TEST_TAKE_PROFIT_PRICE = 322.34


print("=" * 60)
print("IBKR PAPER ORDER TEST")
print("=" * 60)

app = IBConnection()

print("Connecting to TWS Paper...")

app.connect(
    "127.0.0.1",
    7497,
    clientId=20,
)

api_thread = threading.Thread(
    target=run_loop,
    args=(app,),
    daemon=True,
)

api_thread.start()

timeout = 10
start_time = time.time()

while (
    not app.connected_successfully
    and time.time() - start_time < timeout
):
    time.sleep(0.1)

if not app.connected_successfully:
    print("FAILED: Could not connect to IBKR.")
    app.disconnect()
    raise SystemExit


start_time = time.time()

while (
    not app.managed_accounts
    and time.time() - start_time < timeout
):
    time.sleep(0.1)

if not app.managed_accounts:
    print("FAILED: No account detected.")
    app.disconnect()
    raise SystemExit


account = app.managed_accounts[0]

if not account.upper().startswith("DU"):
    print("BLOCKED: Account is NOT recognized as PAPER.")
    app.disconnect()
    raise SystemExit


print("PAPER ACCOUNT VERIFIED.")
print(f"Test symbol: {TEST_SYMBOL}")
print(f"Test quantity: {TEST_QUANTITY}")

executor = OrderExecutor(app)

print("\nSending PAPER bracket order...")

executor.place_bracket_order(
    symbol=TEST_SYMBOL,
    action="BUY",
    quantity=TEST_QUANTITY,
    stop_price=TEST_STOP_PRICE,
    take_profit_price=TEST_TAKE_PROFIT_PRICE,
)

print("\nOrder sent. Waiting for IBKR response...")

time.sleep(8)

app.disconnect()

print("\nPAPER ORDER TEST FINISHED.")