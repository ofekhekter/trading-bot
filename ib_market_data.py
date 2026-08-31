from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from technical_analysis import TechnicalAnalyzer

import threading
import time


class MarketDataApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self.bars = []
        self.data_finished = False

    def nextValidId(self, orderId):
        print("Connected to IBKR.")

    def historicalData(self, reqId, bar):
        self.bars.append({
            "date": bar.date,
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": float(bar.volume),
        })

    def historicalDataEnd(self, reqId, start, end):
        self.data_finished = True
        print(f"Historical data received: {len(self.bars)} bars")

    def error(
        self,
        reqId,
        errorTime,
        errorCode,
        errorString,
        advancedOrderRejectJson=""
    ):
        # These are normal IBKR connection status messages
        if errorCode in [2104, 2106, 2158]:
            print(f"IBKR STATUS {errorCode}: {errorString}")
            return

        print(
            f"IBKR ERROR | "
            f"reqId={reqId} | "
            f"code={errorCode} | "
            f"{errorString}"
        )


def create_stock_contract(symbol: str):
    contract = Contract()

    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract


def run_loop(app):
    app.run()
def get_historical_bars(
    symbol: str,
    duration: str = "2 D",
    bar_size: str = "5 mins"
):
    app = MarketDataApp()

    app.connect(
        "127.0.0.1",
        7497,
        clientId=3
    )

    api_thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True
    )

    api_thread.start()

    time.sleep(2)

    contract = create_stock_contract(symbol)

    app.reqHistoricalData(
        reqId=1,
        contract=contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow="TRADES",
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    timeout = 20
    started = time.time()

    while not app.data_finished:
        if time.time() - started > timeout:
            break

        time.sleep(0.25)

    bars = app.bars.copy()

    app.disconnect()

    return bars

if __name__ == "__main__":

    app = MarketDataApp()

    print("Connecting to TWS Paper...")

    app.connect(
        "127.0.0.1",
        7497,
        clientId=2
    )

    api_thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True
    )

    api_thread.start()

    time.sleep(2)

    nvda = create_stock_contract("NVDA")

    print("Requesting NVDA historical data...")

    app.reqHistoricalData(
        reqId=1,
        contract=nvda,
        endDateTime="",
        durationStr="2 D",
        barSizeSetting="5 mins",
        whatToShow="TRADES",
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    timeout = 20
    started = time.time()

    while not app.data_finished:
        if time.time() - started > timeout:
            print("Timed out waiting for data.")
            break

        time.sleep(0.25)

    if app.bars:
        print("\nLast 10 bars:")

        for bar in app.bars[-10:]:
            print(
                f"{bar['date']} | "
                f"O {bar['open']:.2f} | "
                f"H {bar['high']:.2f} | "
                f"L {bar['low']:.2f} | "
                f"C {bar['close']:.2f} | "
                f"V {bar['volume']:.0f}"
            )
        print("\n--- REAL NVDA TECHNICAL ANALYSIS ---")

        closes = [
            bar["close"]
            for bar in app.bars
        ]

        technical_analyzer = TechnicalAnalyzer()

        technical_result = technical_analyzer.calculate_score(
            closes
        )

        print(f"Current price: ${technical_result['current_price']}")
        print(f"EMA20: {technical_result['ema20']}")
        print(f"EMA50: {technical_result['ema50']}")
        print(f"RSI14: {technical_result['rsi14']}")
        print(
            f"Momentum: "
            f"{technical_result['momentum_percent']}%"
        )
        print(
            f"Technical score: "
            f"{technical_result['technical_score']}/100"
        )    

    app.disconnect()