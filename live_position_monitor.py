import os
import threading
import time

from dotenv import load_dotenv
from ibapi.execution import ExecutionFilter

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

from alpaca_market_data import AlpacaMarketData
from ib_connection import IBConnection, run_loop
from market_data_guard import MarketDataGuard
from position_manager import PositionManager
from position_reconciler import PositionReconciler
from position_state import PositionStateStore


TARGET_SYMBOL = "AAPL"

IBKR_HOST = "127.0.0.1"
IBKR_PORT = 7497
IBKR_CLIENT_ID = 40

IBKR_TIMEOUT_SECONDS = 10
ALPACA_STREAM_WAIT_SECONDS = 5
MARKET_DATA_MAX_AGE_SECONDS = 30


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
        print("\nPOSITIONS DOWNLOAD FINISHED")

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
                "quantity": float(order.totalQuantity),
                "limit_price": float(order.lmtPrice),
                "stop_price": float(order.auxPrice),
                "parent_id": order.parentId,
                "status": orderState.status,
            }
        )

    def openOrderEnd(self):
        self.open_orders_finished = True
        print("\nOPEN ORDERS DOWNLOAD FINISHED")

    def execDetailsEnd(
        self,
        reqId,
    ):
        self.executions_finished = True
        print("\nEXECUTIONS DOWNLOAD FINISHED")


def wait_for_flag(
    condition,
    timeout_seconds,
    timeout_message,
):
    timeout = time.time() + timeout_seconds

    while not condition():
        if time.time() > timeout:
            print(timeout_message)
            return False

        time.sleep(0.1)

    return True


def get_alpaca_rest_latest_trade(
    symbol,
):
    load_dotenv()

    api_key = os.getenv(
        "ALPACA_API_KEY"
    )

    secret_key = os.getenv(
        "ALPACA_SECRET_KEY"
    )

    if not api_key or not secret_key:
        raise RuntimeError(
            "Alpaca API credentials were not found in .env"
        )

    client = StockHistoricalDataClient(
        api_key,
        secret_key,
    )

    request = StockLatestTradeRequest(
        symbol_or_symbols=symbol,
        feed=DataFeed.IEX,
    )

    trades = client.get_stock_latest_trade(
        request
    )

    trade = trades[symbol]

    return {
        "price": float(trade.price),
        "timestamp": trade.timestamp,
        "source": "ALPACA IEX REST LATEST TRADE",
    }


def get_current_market_price(
    symbol,
):
    market_data = AlpacaMarketData()

    try:
        market_data.subscribe_symbol(
            symbol
        )

        market_data.start()

        print(
            "\nWaiting for Alpaca IEX "
            "WebSocket market data..."
        )

        timeout = (
            time.time()
            + ALPACA_STREAM_WAIT_SECONDS
        )

        while time.time() < timeout:
            price = (
                market_data.get_latest_price(
                    symbol
                )
            )

            if price is not None:
                timestamp = (
                    market_data.get_latest_timestamp(
                        symbol
                    )
                )

                return {
                    "price": float(price),
                    "timestamp": timestamp,
                    "source": "ALPACA IEX WEBSOCKET",
                }

            time.sleep(0.1)

        print(
            "No new WebSocket trade received "
            "during startup window."
        )

        print(
            "Falling back to Alpaca IEX "
            "latest trade REST..."
        )

        return get_alpaca_rest_latest_trade(
            symbol
        )

    finally:
        market_data.stop()


def main():

    print("=" * 60)
    print(
        "LIVE POSITION MONITOR "
        "- ALPACA MARKET DATA "
        "- DRY RUN"
    )
    print("=" * 60)

    print(
        "NO ORDERS WILL BE MODIFIED."
    )

    app = LiveMonitorApp()

    try:
        app.connect(
            IBKR_HOST,
            IBKR_PORT,
            clientId=IBKR_CLIENT_ID,
        )

        api_thread = threading.Thread(
            target=run_loop,
            args=(app,),
            daemon=True,
        )

        api_thread.start()

        # =====================================
        # WAIT FOR IBKR CONNECTION
        # =====================================

        connected = wait_for_flag(
            lambda: app.connected_successfully,
            IBKR_TIMEOUT_SECONDS,
            "FAILED: Could not connect to IBKR.",
        )

        if not connected:
            raise SystemExit

        # =====================================
        # VERIFY PAPER ACCOUNT
        # =====================================

        account_found = wait_for_flag(
            lambda: bool(
                app.managed_accounts
            ),
            IBKR_TIMEOUT_SECONDS,
            "FAILED: No IBKR account detected.",
        )

        if not account_found:
            raise SystemExit

        account = app.managed_accounts[0]

        if not account.upper().startswith(
            "DU"
        ):
            print(
                "BLOCKED: Connected account "
                "is NOT PAPER."
            )

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

        positions_done = wait_for_flag(
            lambda: app.positions_finished,
            IBKR_TIMEOUT_SECONDS,
            "Timed out waiting for positions.",
        )

        if not positions_done:
            raise SystemExit

        # =====================================
        # REQUEST OPEN ORDERS
        # =====================================

        print(
            "\nRequesting open orders..."
        )

        app.reqAllOpenOrders()

        open_orders_done = wait_for_flag(
            lambda: app.open_orders_finished,
            IBKR_TIMEOUT_SECONDS,
            "Timed out waiting for open orders.",
        )

        if not open_orders_done:
            raise SystemExit

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

        executions_done = wait_for_flag(
            lambda: app.executions_finished,
            IBKR_TIMEOUT_SECONDS,
            "Timed out waiting for executions.",
        )

        if not executions_done:
            raise SystemExit

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

            raise SystemExit

        position_size = float(
            target_position["position"]
        )

        print(
            "\n" + "=" * 60
        )
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

            raise SystemExit

        print(
            f"Side: {side}"
        )

        # =====================================
        # FIND ENTRY EXECUTION
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

        # =====================================
        # LOAD PERSISTENT STATE
        # =====================================

        state_store = (
            PositionStateStore()
        )

        stored_state = (
            state_store.get(
                TARGET_SYMBOL
            )
        )

        state_matches_position = False

        if stored_state is not None:
            stored_side = str(
                stored_state.get(
                    "side",
                    "",
                )
            ).upper()

            stored_quantity = float(
                stored_state.get(
                    "quantity",
                    0,
                )
            )

            state_matches_position = (
                stored_side == side
                and abs(
                    stored_quantity
                    - abs(position_size)
                ) < 0.000001
            )

            if state_matches_position:
                print(
                    "\nPersistent position "
                    "state found."
                )

            else:
                print(
                    "\nWARNING: Stored position "
                    "state does not match the "
                    "current IBKR position."
                )

        # =====================================
        # DETERMINE ENTRY PRICE
        # =====================================

        if (
            state_matches_position
            and float(
                stored_state.get(
                    "entry_price",
                    0,
                )
            ) > 0
        ):
            entry_price = float(
                stored_state[
                    "entry_price"
                ]
            )

            entry_price_source = str(
                stored_state.get(
                    "entry_price_source",
                    "PERSISTENT STATE",
                )
            )

            print(
                "\nUsing persisted "
                "entry price."
            )

        elif entry_execution is not None:
            entry_price = float(
                entry_execution["price"]
            )

            entry_price_source = (
                "IBKR EXECUTION"
            )

        else:
            entry_price = float(
                target_position["avg_cost"]
            )

            entry_price_source = (
                "IBKR AVG COST FALLBACK"
            )

            print(
                "\nNo matching execution was "
                "returned for this older "
                "open position."
            )

            print(
                "Using IBKR Avg Cost as a "
                "DRY-RUN entry-price fallback."
            )

        print(
            f"Entry price: "
            f"{entry_price:.2f}"
        )

        print(
            f"Entry price source: "
            f"{entry_price_source}"
        )

        # =====================================
        # FIND CURRENT STOP ORDER
        # =====================================

        stop_order = None

        for order in app.open_orders:
            if (
                order["symbol"].upper()
                == TARGET_SYMBOL
                and order[
                    "order_type"
                ].upper() == "STP"
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
        # GET CURRENT PRICE FROM ALPACA
        # =====================================

        print(
            "\nRequesting current market "
            "price from Alpaca..."
        )

        market_quote = (
            get_current_market_price(
                TARGET_SYMBOL
            )
        )

        current_price = float(
            market_quote["price"]
        )

        print(
            "\n" + "=" * 60
        )
        print("ALPACA MARKET DATA")
        print("=" * 60)

        print(
            f"Source: "
            f"{market_quote['source']}"
        )

        print(
            f"Market price: "
            f"{current_price:.2f}"
        )

        print(
            f"Timestamp: "
            f"{market_quote['timestamp']}"
        )

        # =====================================
        # MARKET DATA FRESHNESS GUARD
        # =====================================

        market_guard = MarketDataGuard(
            max_age_seconds=(
                MARKET_DATA_MAX_AGE_SECONDS
            )
        )

        market_safety = (
            market_guard.evaluate(
                market_quote[
                    "timestamp"
                ]
            )
        )

        market_data_fresh = bool(
            market_safety["fresh"]
        )

        market_data_age = (
            market_safety[
                "age_seconds"
            ]
        )

        market_data_reason = (
            market_safety["reason"]
        )

        print(
            "\n" + "=" * 60
        )
        print(
            "MARKET DATA SAFETY"
        )
        print("=" * 60)

        print(
            f"Fresh: "
            f"{market_data_fresh}"
        )

        print(
            f"Age seconds: "
            f"{market_data_age}"
        )

        print(
            f"Reason: "
            f"{market_data_reason}"
        )

        # =====================================
        # RESTORE HIGH / LOW WATER MARKS
        # =====================================

        if state_matches_position:
            highest_price = float(
                stored_state.get(
                    "highest_price",
                    entry_price,
                )
            )

            lowest_price = float(
                stored_state.get(
                    "lowest_price",
                    entry_price,
                )
            )

        else:
            highest_price = entry_price
            lowest_price = entry_price

        # IMPORTANT:
        # Stale data is not allowed to modify
        # persistent high/low water marks.

        if market_data_fresh:
            highest_price = max(
                highest_price,
                current_price,
            )

            lowest_price = min(
                lowest_price,
                current_price,
            )

        else:
            print(
                "\nSTALE DATA GUARD: "
                "high/low water marks "
                "will NOT be updated."
            )

        print(
            f"Highest price tracked: "
            f"{highest_price:.2f}"
        )

        print(
            f"Lowest price tracked: "
            f"{lowest_price:.2f}"
        )

        # =====================================
        # POSITION MANAGER
        # =====================================

        manager = PositionManager()

        if side == "LONG":
            result = manager.calculate_stop(
                side="LONG",
                entry_price=entry_price,
                current_price=current_price,
                highest_price=highest_price,
                current_stop=current_stop,
            )

        else:
            result = manager.calculate_stop(
                side="SHORT",
                entry_price=entry_price,
                current_price=current_price,
                lowest_price=lowest_price,
                current_stop=current_stop,
            )

        suggested_stop = float(
            result["suggested_stop"]
        )

        print(
            "\n" + "=" * 60
        )
        print(
            "POSITION MANAGER DECISION"
        )
        print("=" * 60)

        print(
            f"Stage: "
            f"{result['stage']}"
        )

        print(
            f"Current move: "
            f"{result['current_move_percent']:.3f}%"
        )

        print(
            f"Favorable move: "
            f"{result['favorable_move_percent']:.3f}%"
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
        # POSITION RECONCILER
        # =====================================

        reconciler = (
            PositionReconciler()
        )

        reconciliation = (
            reconciler.evaluate(
                side=side,
                current_price=current_price,
                suggested_stop=suggested_stop,
                current_stop=current_stop,
            )
        )

        reconciliation_action = (
            reconciliation["action"]
        )

        reconciliation_reason = (
            reconciliation["reason"]
        )

        protection_breached = (
            reconciliation_action
            == "EXIT_REQUIRED"
        )

        print(
            "\n" + "=" * 60
        )
        print(
            "RECONCILIATION DECISION"
        )
        print("=" * 60)

        print(
            f"Action: "
            f"{reconciliation_action}"
        )

        print(
            f"Reason: "
            f"{reconciliation_reason}"
        )

        # =====================================
        # EXECUTION SAFETY
        # =====================================

        execution_allowed = (
            market_data_fresh
        )

        execution_block_reason = (
            None
            if execution_allowed
            else market_data_reason
        )

        print(
            "\n" + "=" * 60
        )
        print(
            "EXECUTION SAFETY"
        )
        print("=" * 60)

        print(
            f"Reconciliation action: "
            f"{reconciliation_action}"
        )

        print(
            f"Market data fresh: "
            f"{market_data_fresh}"
        )

        print(
            f"Execution allowed: "
            f"{execution_allowed}"
        )

        print(
            f"Block reason: "
            f"{execution_block_reason}"
        )

        # =====================================
        # DETERMINE SAFE PERSISTENT
        # MARKET DATA VALUES
        # =====================================

        if market_data_fresh:
            persistent_market_price = round(
                current_price,
                4,
            )

            persistent_market_timestamp = str(
                market_quote[
                    "timestamp"
                ]
            )

        elif state_matches_position:
            persistent_market_price = (
                stored_state.get(
                    "last_market_price"
                )
            )

            persistent_market_timestamp = (
                stored_state.get(
                    "last_market_timestamp"
                )
            )

        else:
            persistent_market_price = None
            persistent_market_timestamp = None

        # =====================================
        # SAVE PERSISTENT STATE
        # =====================================

        state_store.save(
            TARGET_SYMBOL,
            {
                "side": side,

                "quantity": abs(
                    position_size
                ),

                "entry_price": round(
                    entry_price,
                    4,
                ),

                "entry_price_source": (
                    entry_price_source
                ),

                "highest_price": round(
                    highest_price,
                    4,
                ),

                "lowest_price": round(
                    lowest_price,
                    4,
                ),

                "broker_stop": (
                    round(
                        current_stop,
                        4,
                    )
                    if current_stop
                    is not None
                    else None
                ),

                "last_calculated_stop": round(
                    suggested_stop,
                    4,
                ),

                "stage": (
                    result["stage"]
                ),

                "current_move_percent": (
                    result[
                        "current_move_percent"
                    ]
                ),

                "favorable_move_percent": (
                    result[
                        "favorable_move_percent"
                    ]
                ),

                "last_market_price": (
                    persistent_market_price
                ),

                "last_market_timestamp": (
                    persistent_market_timestamp
                ),

                "market_data_source": (
                    market_quote[
                        "source"
                    ]
                ),

                "market_data_fresh": (
                    market_data_fresh
                ),

                "market_data_age_seconds": (
                    market_data_age
                ),

                "market_data_guard_reason": (
                    market_data_reason
                ),

                "reconciliation_action": (
                    reconciliation_action
                ),

                "reconciliation_reason": (
                    reconciliation_reason
                ),

                "protection_breached": (
                    protection_breached
                ),

                "execution_allowed": (
                    execution_allowed
                ),

                "execution_block_reason": (
                    execution_block_reason
                ),
            },
        )

        print(
            "\nPersistent state saved "
            "to position_state.json"
        )

        # =====================================
        # DRY RUN ACTION SUMMARY
        # =====================================

        print(
            "\n" + "=" * 60
        )
        print(
            "DRY RUN ACTION SUMMARY"
        )
        print("=" * 60)

        if not execution_allowed:
            print(
                "ACTION BLOCKED - "
                "MARKET DATA IS NOT FRESH"
            )

            print(
                f"Requested action: "
                f"{reconciliation_action}"
            )

            print(
                f"Block reason: "
                f"{execution_block_reason}"
            )

        elif (
            reconciliation_action
            == "EXIT_REQUIRED"
        ):
            print(
                "WOULD EXIT POSITION"
            )

        elif (
            reconciliation_action
            == "CREATE_STOP_REQUIRED"
        ):
            print(
                f"WOULD CREATE STOP "
                f"AT {suggested_stop:.2f}"
            )

        elif (
            reconciliation_action
            == "RAISE_STOP"
        ):
            print(
                f"WOULD RAISE STOP | "
                f"{current_stop:.2f} "
                f"-> {suggested_stop:.2f}"
            )

        elif (
            reconciliation_action
            == "LOWER_STOP"
        ):
            print(
                f"WOULD LOWER STOP | "
                f"{current_stop:.2f} "
                f"-> {suggested_stop:.2f}"
            )

        elif (
            reconciliation_action
            == "NO_ACTION"
        ):
            print(
                "NO ACTION REQUIRED"
            )

        else:
            print(
                "UNKNOWN RECONCILIATION ACTION"
            )

        print()
        print(
            "DRY RUN ONLY - "
            "NO ORDER WAS SENT OR MODIFIED."
        )

    finally:
        if app.isConnected():
            app.disconnect()


if __name__ == "__main__":
    main()