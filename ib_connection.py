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

    def nextValidId(self, orderId):
        super().nextValidId(orderId)

        self.next_order_id = orderId
        self.connected_successfully = True

        print("=" * 50)
        print("CONNECTED TO INTERACTIVE BROKERS")
        print(f"Next valid order ID: {orderId}")
        print("=" * 50)

        # Ask IBKR which accounts this API session can access
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


def run_loop(app):
    app.run()


if __name__ == "__main__":

    app = IBConnection()

    print("Connecting to TWS...")

    app.connect(
        "127.0.0.1",
        7497,
        clientId=1
    )

    api_thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True
    )

    api_thread.start()

    time.sleep(3)

    if app.connected_successfully:
        print("API connection test PASSED")
    else:
        print("API connection test FAILED")

    print(f"Accounts detected: {app.managed_accounts}")

    app.disconnect()