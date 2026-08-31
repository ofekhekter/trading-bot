from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

import threading
import time
from datetime import datetime, timedelta


class NewsTestApp(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

        self.con_id = None
        self.contract_finished = False
        self.news_finished = False
        self.headlines = []
        self.seen_headlines = set()
        self.news_cutoff = datetime.utcnow() - timedelta(hours=96)

    def nextValidId(self, orderId):
        print("Connected to IBKR.")

    def contractDetails(self, reqId, contractDetails):
        self.con_id = contractDetails.contract.conId

        print(
            f"NVDA contract found | "
            f"conId={self.con_id}"
        )

    def contractDetailsEnd(self, reqId):
        self.contract_finished = True

    def historicalNews(
        self,
        requestId,
        time,
        providerCode,
        articleId,
        headline
    ):
        try:
            news_time = datetime.strptime(
                time,
                "%Y-%m-%d %H:%M:%S.%f"
            )
        except ValueError:
            print(f"Could not parse news time: {time}")
            return

        if news_time < self.news_cutoff:
            return
        clean_key = headline.strip().lower()

        if clean_key in self.seen_headlines:
            return

        self.seen_headlines.add(clean_key)

        self.headlines.append({
            "time": time,
            "provider": providerCode,
            "article_id": articleId,
            "headline": headline
        })

    def historicalNewsEnd(
        self,
        requestId,
        hasMore
    ):
        self.news_finished = True

        print(
            f"\nHistorical news finished | "
            f"hasMore={hasMore}"
        )

    def error(
        self,
        reqId,
        errorTime,
        errorCode,
        errorString,
        advancedOrderRejectJson=""
    ):
        if errorCode in [2104, 2106, 2158]:
            return

        print(
            f"IBKR ERROR | "
            f"reqId={reqId} | "
            f"code={errorCode} | "
            f"{errorString}"
        )


def run_loop(app):
    app.run()


def create_stock_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract
def get_recent_news(
    symbol: str,
    providers: str = "BRFG+BRFUPDN+DJNL"
):
    app = NewsTestApp()

    app.connect(
        "127.0.0.1",
        7497,
        clientId=5
    )

    thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True
    )

    thread.start()

    time.sleep(2)

    contract = create_stock_contract(symbol)

    app.reqContractDetails(
        10,
        contract
    )

    timeout = time.time() + 10

    while not app.contract_finished:
        if time.time() > timeout:
            app.disconnect()
            return []

        time.sleep(0.2)

    if app.con_id is None:
        app.disconnect()
        return []

    end = datetime.utcnow()
    start = end - timedelta(hours=96)

    end_time = end.strftime(
        "%Y%m%d-%H:%M:%S"
    )

    start_time = start.strftime(
        "%Y%m%d-%H:%M:%S"
    )

    app.reqHistoricalNews(
        20,
        app.con_id,
        providers,
        start_time,
        end_time,
        50,
        []
    )

    timeout = time.time() + 15

    while not app.news_finished:
        if time.time() > timeout:
            break

        time.sleep(0.2)

    headlines = app.headlines.copy()

    app.disconnect()

    return headlines

if __name__ == "__main__":

    app = NewsTestApp()

    print("Connecting to TWS Paper...")

    app.connect(
        "127.0.0.1",
        7497,
        clientId=4
    )

    thread = threading.Thread(
        target=run_loop,
        args=(app,),
        daemon=True
    )

    thread.start()

    time.sleep(2)

    # --------------------------------
    # Find NVDA conId
    # --------------------------------

    print("\nFinding NVDA contract...")

    contract = create_stock_contract("NVDA")

    app.reqContractDetails(
        10,
        contract
    )

    timeout = time.time() + 10

    while not app.contract_finished:

        if time.time() > timeout:
            print("Timed out finding NVDA contract.")
            app.disconnect()
            raise SystemExit

        time.sleep(0.2)


    if app.con_id is None:
        print("Could not find NVDA conId.")
        app.disconnect()
        raise SystemExit


    # --------------------------------
    # Request real NVDA news
    # --------------------------------

    end = datetime.utcnow()

    start = end - timedelta(days=7)

    end_time = end.strftime(
        "%Y%m%d-%H:%M:%S"
    )

    start_time = start.strftime(
        "%Y%m%d-%H:%M:%S"
    )

    providers = "BRFG+BRFUPDN+DJNL"

    print("\nRequesting REAL NVDA news...")

    app.reqHistoricalNews(
        20,
        app.con_id,
        providers,
        start_time,
        end_time,
        50,
        []
    )

    timeout = time.time() + 15

    while not app.news_finished:

        if time.time() > timeout:
            print("Timed out waiting for news.")
            break

        time.sleep(0.2)


    # --------------------------------
    # Print results
    # --------------------------------

    print(
        f"\n--- REAL NVDA NEWS "
        f"({len(app.headlines)} articles) ---"
    )

    for article in app.headlines:

        print(
            f"\n[{article['provider']}] "
            f"{article['time']}"
        )

        print(article["headline"])


    app.disconnect()