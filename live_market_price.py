from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

import threading
import time


TARGET_SYMBOL = "AAPL"


class LivePriceApp(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

        self.connected_successfully = False

        self.bid = None
        self.ask = None
        self.last = None
        self.close = None

        self.market_data_type = None

    def nextValidId(self, orderId):
        self.connected_successfully = True

        print("=" * 50)
        print("CONNECTED TO INTERACTIVE BROKERS")
        print(f"Next valid order ID: {orderId}")
        print("=" * 50)

    def marketDataType(
        self,
        reqId,
        marketDataType,
    ):
        self.market_data_type = marketDataType

        print(
            f"Market data type: "
            f"{marketDataType}"
        )

    def tickPrice(
        self,
        reqId,
        tickType,
        price,
        attrib,
    ):
        if price <= 0:
            return

        # IBKR Tick Types:
        # 1 = BID
        # 2 = ASK
        # 4 = LAST
        # 9 = CLOSE

        if tickType == 1:
            self.bid = float(price)

            print(
                f"BID: "
                f"${self.bid:.2f}"
            )

        elif tickType == 2:
            self.ask = float(price)

            print(
                f"ASK: "
                f"${self.ask:.2f}"
            )

        elif tickType == 4:
            self.last = float(price)

            print(
                f"LAST: "
                f"${self.last:.2f}"
            )

        elif tickType == 9:
            self.close = float(price)

            print(
                f"CLOSE: "
                f"${self.close:.2f}"
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


def create_stock_contract(
    symbol
):
    contract = Contract()

    contract.symbol = symbol.upper()
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract


print("=" * 60)
print("IBKR LIVE MARKET PRICE TEST")
print("=" * 60)

print(
    f"Symbol: {TARGET_SYMBOL}"
)

print(
    "READ-ONLY TEST - "
    "NO ORDERS WILL BE SENT."
)

app = LivePriceApp()

app.connect(
    "127.0.0.1",
    7497,
    clientId=50,
)

api_thread = threading.Thread(
    target=run_loop,
    args=(app,),
    daemon=True,
)

api_thread.start()


# =====================================
# WAIT FOR API CONNECTION
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


contract = create_stock_contract(
    TARGET_SYMBOL
)


# =====================================
# REQUEST MARKET DATA
# =====================================
#
# 1 = Live
# 2 = Frozen
# 3 = Delayed
# 4 = Delayed Frozen
#
# We first request LIVE.
# IBKR may return a different data type
# depending on the account subscriptions.
# =====================================

app.reqMarketDataType(1)

print(
    "\nRequesting market data..."
)

app.reqMktData(
    100,
    contract,
    "",
    False,
    False,
    [],
)


# =====================================
# WAIT FOR PRICE
# =====================================

timeout = time.time() + 10

while time.time() < timeout:

    if (
        app.last is not None
        or (
            app.bid is not None
            and app.ask is not None
        )
    ):
        break

    time.sleep(0.1)


# =====================================
# SELECT BEST CURRENT PRICE
# =====================================

print("\n" + "=" * 60)
print("MARKET PRICE RESULT")
print("=" * 60)

current_price = None
source = None

if app.last is not None:

    current_price = app.last
    source = "LAST"

elif (
    app.bid is not None
    and app.ask is not None
):

    current_price = (
        app.bid + app.ask
    ) / 2

    source = "MID"

elif app.bid is not None:

    current_price = app.bid
    source = "BID"

elif app.ask is not None:

    current_price = app.ask
    source = "ASK"

elif app.close is not None:

    current_price = app.close
    source = "CLOSE"


if current_price is None:

    print(
        "No usable market price "
        "was received."
    )

else:

    print(
        f"Bid: "
        f"{app.bid}"
    )

    print(
        f"Ask: "
        f"{app.ask}"
    )

    print(
        f"Last: "
        f"{app.last}"
    )

    print(
        f"Close: "
        f"{app.close}"
    )

    print(
        f"Selected price: "
        f"${current_price:.2f}"
    )

    print(
        f"Price source: "
        f"{source}"
    )

    print(
        f"Market data type: "
        f"{app.market_data_type}"
    )


app.cancelMktData(100)

time.sleep(0.5)

app.disconnect()

print(
    "\nLIVE MARKET PRICE TEST FINISHED."
)