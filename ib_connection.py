from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time


class IBConnection(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.connected_successfully = False

    def nextValidId(self, orderId):
        super().nextValidId(orderId)

        self.connected_successfully = True

        print("=" * 50)
        print("CONNECTED TO INTERACTIVE BROKERS")
        print(f"Next valid order ID: {orderId}")
        print("=" * 50)


def run_loop(app):
    app.run()


if __name__ == "__main__":

    app = IBConnection()

    print("Connecting to TWS Paper Trading...")

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

    app.disconnect()