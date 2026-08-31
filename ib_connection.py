from ibapi.client import EClient
from ibapi.wrapper import EWrapper

import threading
import time


class IBConnection(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

        self.connected_successfully = False
        self.next_order_id = None
        self.managed_accounts = []

        # Track order state
        self.order_statuses = {}
        self.executions = []

    def nextValidId(self, orderId):
        super().nextValidId(orderId)

        self.next_order_id = orderId
        self.connected_successfully = True

        print("=" * 50)
        print("CONNECTED TO INTERACTIVE BROKERS")
        print(f"Next valid order ID: {orderId}")
        print("=" * 50)

        self.reqManagedAccts()

    def managedAccounts(self, accountsList):
        accounts = [
            account.strip()
            for account in accountsList.split(",")
            if account.strip()
        ]

        self.managed_accounts = accounts

        print("Managed accounts:")

        for account in accounts:
            print(f" - {account}")

    def orderStatus(
        self,
        orderId,
        status,
        filled,
        remaining,
        avgFillPrice,
        permId,
        parentId,
        lastFillPrice,
        clientId,
        whyHeld,
        mktCapPrice,
    ):
        self.order_statuses[orderId] = {
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avg_fill_price": avgFillPrice,
            "last_fill_price": lastFillPrice,
            "parent_id": parentId,
        }

        print(
            f"ORDER STATUS | "
            f"ID={orderId} | "
            f"Status={status} | "
            f"Filled={filled} | "
            f"Remaining={remaining} | "
            f"AvgFill={avgFillPrice}"
        )

    def execDetails(
        self,
        reqId,
        contract,
        execution,
    ):
        execution_data = {
            "symbol": contract.symbol,
            "order_id": execution.orderId,
            "side": execution.side,
            "shares": execution.shares,
            "price": execution.price,
            "exec_id": execution.execId,
            "time": execution.time,
        }

        self.executions.append(
            execution_data
        )

        print(
            f"EXECUTION | "
            f"{contract.symbol} | "
            f"OrderID={execution.orderId} | "
            f"Side={execution.side} | "
            f"Shares={execution.shares} | "
            f"Price={execution.price}"
        )

    def openOrder(
        self,
        orderId,
        contract,
        order,
        orderState,
    ):
        print(
            f"OPEN ORDER | "
            f"ID={orderId} | "
            f"{contract.symbol} | "
            f"{order.action} | "
            f"{order.orderType} | "
            f"Qty={order.totalQuantity} | "
            f"Status={orderState.status}"
        )

    def error(
        self,
        reqId,
        errorTime,
        errorCode,
        errorString,
        advancedOrderRejectJson="",
    ):
        if errorCode in [
            2104,
            2106,
            2158,
        ]:
            print(
                f"IBKR STATUS {errorCode}: "
                f"{errorString}"
            )
            return

        print(
            f"IBKR ERROR | "
            f"reqId={reqId} | "
            f"code={errorCode} | "
            f"{errorString}"
        )


def run_loop(app):
    app.run()


if __name__ == "__main__":

    app = IBConnection()

    print("Connecting to TWS...")

    app.connect(
        "127.0.0.1",
        7497,
        clientId=1,
    )

    api_thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True,
    )

    api_thread.start()

    time.sleep(3)

    if app.connected_successfully:
        print("API connection test PASSED")
    else:
        print("API connection test FAILED")

    print(
        f"Accounts detected: "
        f"{app.managed_accounts}"
    )

    app.disconnect()