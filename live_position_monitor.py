import threading
import time

from ibapi.execution import ExecutionFilter

from ib_connection import (
    IBConnection,
    run_loop,
)

from position_manager import (
    PositionManager,
)


TARGET_SYMBOL = "AAPL"


class LiveMonitorApp(IBConnection):

    def __init__(self):
        super().__init__()

        self.positions = []
        self.positions_finished = False

        self.open_orders = []
        self.open_orders_finished = False

        self.executions_finished = False

    def position(
        self,
        account,
        contract,
        position,
        avgCost,
    ):
        self.positions.append(
            {
                "account": account,
                "symbol": contract.symbol,
                "position": float(position),
                "avg_cost": float(avgCost),
            }
        )

    def positionEnd(self):
        self.positions_finished = True

        print(
            "\nPOSITIONS DOWNLOAD FINISHED"
        )

    def openOrder(
        self,
        orderId,
        contract,
        order,
        orderState,
    ):
        super().openOrder(
            orderId,
            contract,
            order,
            orderState,
        )

        self.open_orders.append(
            {
                "order_id": orderId,
                "symbol": contract.symbol,
                "action": order.action,
                "order_type": order.orderType,
                "quantity": float(
                    order.totalQuantity
                ),
                "limit_price": float(
                    order.lmtPrice
                ),
                "stop_price": float(
                    order.auxPrice
                ),
                "parent_id": order.parentId,
                "status": orderState.status,
            }
        )

    def openOrderEnd(self):
        self.open_orders_finished = True

        print(
            "\nOPEN ORDERS DOWNLOAD FINISHED"
        )

    def execDetailsEnd(
        self,
        reqId,
    ):
        self.executions_finished = True

        print(
            "\nEXECUTIONS DOWNLOAD FINISHED"
        )


print("=" * 60)
print("LIVE POSITION MONITOR - DRY RUN")
print("=" * 60)

print(
    "NO ORDERS WILL BE MODIFIED."
)

app = LiveMonitorApp()

app.connect(
    "127.0.0.1",
    7497,
    clientId=40,
)

api_thread = threading.Thread(
    target=run_loop,
    args=(app,),
    daemon=True,
)

api_thread.start()


# =====================================
# WAIT FOR CONNECTION
# =====================================

timeout = time.time() + 10

while not app.connected_successfully:

    if time.time() > timeout:
        print(
            "FAILED: Could not connect "
            "to IBKR."
        )

        app.disconnect()
        raise SystemExit

    time.sleep(0.1)


# =====================================
# WAIT FOR ACCOUNT
# =====================================

timeout = time.time() + 10

while not app.managed_accounts:

    if time.time() > timeout:
        print(
            "FAILED: No IBKR account "
            "detected."
        )

        app.disconnect()
        raise SystemExit

    time.sleep(0.1)


account = app.managed_accounts[0]

if not account.upper().startswith("DU"):

    print(
        "BLOCKED: Connected account "
        "is NOT PAPER."
    )

    app.disconnect()
    raise SystemExit


print(
    "\nPAPER ACCOUNT VERIFIED."
)


# =====================================
# REQUEST POSITIONS
# =====================================

print(
    "\nRequesting positions..."
)

app.reqPositions()

timeout = time.time() + 10

while not app.positions_finished:

    if time.time() > timeout:
        print(
            "Timed out waiting "
            "for positions."
        )
        break

    time.sleep(0.1)


# =====================================
# REQUEST OPEN ORDERS
# =====================================

print(
    "\nRequesting open orders..."
)

app.reqAllOpenOrders()

timeout = time.time() + 10

while not app.open_orders_finished:

    if time.time() > timeout:
        print(
            "Timed out waiting "
            "for open orders."
        )
        break

    time.sleep(0.1)


# =====================================
# REQUEST EXECUTIONS
# =====================================

print(
    "\nRequesting executions..."
)

execution_filter = ExecutionFilter()
execution_filter.acctCode = account

app.reqExecutions(
    200,
    execution_filter,
)

timeout = time.time() + 10

while not app.executions_finished:

    if time.time() > timeout:
        print(
            "Timed out waiting "
            "for executions."
        )
        break

    time.sleep(0.1)


# =====================================
# FIND TARGET POSITION
# =====================================

target_position = None

for position in app.positions:

    if (
        position["symbol"].upper()
        == TARGET_SYMBOL
    ):
        target_position = position
        break


if target_position is None:

    print(
        f"\nNo open position found "
        f"for {TARGET_SYMBOL}."
    )

    app.disconnect()
    raise SystemExit


position_size = (
    target_position["position"]
)

print("\n" + "=" * 60)
print("POSITION FOUND")
print("=" * 60)

print(
    f"Symbol: {TARGET_SYMBOL}"
)

print(
    f"Position size: "
    f"{position_size}"
)

print(
    f"IBKR Avg Cost: "
    f"{target_position['avg_cost']:.2f}"
)


# =====================================
# DETERMINE SIDE
# =====================================

if position_size > 0:
    side = "LONG"

elif position_size < 0:
    side = "SHORT"

else:
    print(
        "Position size is zero."
    )

    app.disconnect()
    raise SystemExit


print(
    f"Side: {side}"
)


# =====================================
# FIND REAL ENTRY EXECUTION
# =====================================

symbol_executions = [
    execution
    for execution in app.executions
    if (
        execution["symbol"].upper()
        == TARGET_SYMBOL
    )
]


entry_execution = None

for execution in reversed(
    symbol_executions
):

    execution_side = (
        execution["side"].upper()
    )

    if (
        side == "LONG"
        and execution_side == "BOT"
    ):
        entry_execution = execution
        break

    if (
        side == "SHORT"
        and execution_side == "SLD"
    ):
        entry_execution = execution
        break


if entry_execution is None:

    print(
        "\nCould not find matching "
        "entry execution."
    )

    app.disconnect()
    raise SystemExit


entry_price = float(
    entry_execution["price"]
)

print(
    f"Real entry price: "
    f"{entry_price:.2f}"
)


# =====================================
# FIND CURRENT STOP ORDER
# =====================================

stop_order = None

for order in app.open_orders:

    if (
        order["symbol"].upper()
        == TARGET_SYMBOL
        and order["order_type"].upper()
        == "STP"
    ):
        stop_order = order
        break


if stop_order is None:

    print(
        "\nWARNING: No active "
        "stop order found."
    )

    current_stop = None

else:

    current_stop = float(
        stop_order["stop_price"]
    )

    print(
        f"Current stop: "
        f"{current_stop:.2f}"
    )

    print(
        f"Stop Order ID: "
        f"{stop_order['order_id']}"
    )


# =====================================
# CURRENT PRICE
# =====================================
#
# For this first DRY RUN we use
# IBKR avgCost only as a safe placeholder
# if no live quote system is connected.
#
# We will replace this in the next step
# with actual market price data.
# =====================================

current_price = float(
    target_position["avg_cost"]
)

print(
    f"\nTemporary current price: "
    f"{current_price:.2f}"
)

print(
    "(Using IBKR avgCost only for "
    "this first dry-run test.)"
)


# =====================================
# CALCULATE SUGGESTED STOP
# =====================================

manager = PositionManager()

if side == "LONG":

    result = manager.calculate_stop(
        side="LONG",
        entry_price=entry_price,
        current_price=current_price,
        highest_price=current_price,
        current_stop=current_stop,
    )

else:

    result = manager.calculate_stop(
        side="SHORT",
        entry_price=entry_price,
        current_price=current_price,
        lowest_price=current_price,
        current_stop=current_stop,
    )


suggested_stop = result[
    "suggested_stop"
]


print("\n" + "=" * 60)
print("POSITION MANAGER DECISION")
print("=" * 60)

print(
    f"Stage: "
    f"{result['stage']}"
)

print(
    f"Move: "
    f"{result['move_percent']:.3f}%"
)

print(
    f"Current stop: "
    f"{current_stop}"
)

print(
    f"Suggested stop: "
    f"{suggested_stop:.2f}"
)


# =====================================
# DRY RUN DECISION
# =====================================

if current_stop is None:

    print(
        "\nWOULD CREATE STOP ORDER"
    )

elif side == "LONG":

    if suggested_stop > current_stop:

        print(
            f"\nWOULD MODIFY STOP | "
            f"{current_stop:.2f} "
            f"-> {suggested_stop:.2f}"
        )

    else:

        print(
            "\nNO STOP CHANGE NEEDED"
        )

else:

    if suggested_stop < current_stop:

        print(
            f"\nWOULD MODIFY STOP | "
            f"{current_stop:.2f} "
            f"-> {suggested_stop:.2f}"
        )

    else:

        print(
            "\nNO STOP CHANGE NEEDED"
        )


print(
    "\nDRY RUN ONLY - "
    "NO ORDER WAS MODIFIED."
)

app.disconnect()