import threading
import time

from ibapi.execution import ExecutionFilter

from ib_connection import (
    IBConnection,
    run_loop,
)


class StateTestApp(IBConnection):

    def __init__(self):
        super().__init__()

        self.open_orders_finished = False
        self.executions_finished = False

    def openOrderEnd(self):
        self.open_orders_finished = True

        print(
            "\nOPEN ORDERS DOWNLOAD FINISHED"
        )

    def execDetailsEnd(self, reqId):
        self.executions_finished = True

        print(
            "\nEXECUTIONS DOWNLOAD FINISHED"
        )


print("=" * 60)
print("IBKR PAPER STATE TEST")
print("=" * 60)

app = StateTestApp()

print("Connecting to TWS Paper...")

app.connect(
    "127.0.0.1",
    7497,
    clientId=30,
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


print("\nPAPER ACCOUNT VERIFIED.")
print(f"Account: {account[:2]}...")


# =====================================
# REQUEST ALL OPEN ORDERS
# =====================================

print("\nRequesting open orders...")

app.reqAllOpenOrders()

timeout = time.time() + 10

while not app.open_orders_finished:

    if time.time() > timeout:
        print(
            "Timed out waiting for "
            "open orders."
        )
        break

    time.sleep(0.1)


# =====================================
# REQUEST EXECUTIONS
# =====================================

print("\nRequesting executions...")

execution_filter = ExecutionFilter()

execution_filter.acctCode = account

app.reqExecutions(
    100,
    execution_filter,
)

timeout = time.time() + 10

while not app.executions_finished:

    if time.time() > timeout:
        print(
            "Timed out waiting for "
            "executions."
        )
        break

    time.sleep(0.1)


# =====================================
# SUMMARY
# =====================================

print("\n" + "=" * 60)
print("EXECUTION SUMMARY")
print("=" * 60)

if not app.executions:

    print(
        "No executions returned."
    )

else:

    for execution in app.executions:

        print(
            f"{execution['symbol']} | "
            f"OrderID={execution['order_id']} | "
            f"Side={execution['side']} | "
            f"Shares={execution['shares']} | "
            f"Price={execution['price']} | "
            f"Time={execution['time']}"
        )


print("\nDisconnecting...")

app.disconnect()

print("STATE TEST FINISHED.")