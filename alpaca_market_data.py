import os
import threading
from typing import Optional

from dotenv import load_dotenv

from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed


class AlpacaMarketData:

    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise RuntimeError(
                "Alpaca API credentials were not found in .env"
            )

        self.stream = StockDataStream(
            self.api_key,
            self.secret_key,
            feed=DataFeed.IEX,
        )

        self.latest_prices = {}
        self.latest_timestamps = {}

        self._thread: Optional[threading.Thread] = None
        self._running = False

    async def _trade_handler(self, trade):
        symbol = trade.symbol
        price = float(trade.price)

        self.latest_prices[symbol] = price
        self.latest_timestamps[symbol] = trade.timestamp

        print(
            f"[ALPACA] "
            f"{symbol} | "
            f"${price:.2f} | "
            f"{trade.timestamp}"
        )

    def subscribe_symbol(self, symbol: str):
        symbol = symbol.upper()

        self.stream.subscribe_trades(
            self._trade_handler,
            symbol,
        )

        print(
            f"Subscribed to Alpaca IEX trades: {symbol}"
        )

    def get_latest_price(
        self,
        symbol: str,
    ) -> Optional[float]:

        return self.latest_prices.get(
            symbol.upper()
        )

    def get_latest_timestamp(
        self,
        symbol: str,
    ):
        return self.latest_timestamps.get(
            symbol.upper()
        )

    def start(self):
        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(
            target=self.stream.run,
            daemon=True,
        )

        self._thread.start()

        print("Alpaca market data stream started.")

    def stop(self):
        if not self._running:
            return

        self._running = False

        try:
            self.stream.stop()
        except Exception as exc:
            print(
                f"Warning while stopping Alpaca stream: {exc}"
            )

        print("Alpaca market data stream stopped.")


if __name__ == "__main__":

    import time

    SYMBOL = "AAPL"

    print("=" * 60)
    print("ALPACA WEBSOCKET MARKET DATA TEST")
    print("READ ONLY - NO ORDERS")
    print("=" * 60)

    market_data = AlpacaMarketData()

    market_data.subscribe_symbol(
        SYMBOL
    )

    market_data.start()

    print()
    print(
        "Listening for real-time trades..."
    )
    print(
        "Press CTRL+C to stop."
    )
    print()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("Stopping...")

    finally:
        market_data.stop()

        print("=" * 60)
        print("TEST FINISHED")
        print("=" * 60)