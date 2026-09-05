import threading
import time

from ibapi.execution import ExecutionFilter

from ib_connection import IBConnection, run_loop
from live_position_monitor import (
    get_current_market_price,
)
from market_data_guard import MarketDataGuard
from paper_execution_manager import (
    PaperExecutionManager,
)
from position_manager import PositionManager
from position_reconciler import PositionReconciler
from position_state import PositionStateStore


TARGET_SYMBOL = "AAPL"

IBKR_HOST = "127.0.0.1"
IBKR_PORT = 7497
IBKR_CLIENT_ID = 60

IBKR_TIMEOUT_SECONDS = 10
MARKET_DATA_MAX_AGE_SECONDS = 30


class IntegrationApp(IBConnection):

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
            "POSITIONS DOWNLOAD FINISHED"
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
                "stop_price": float(
                    order.auxPrice
                ),
                "status": orderState.status,
            }
        )

    def openOrderEnd(self):
        self.open_orders_finished = True

        print(
            "OPEN ORDERS DOWNLOAD FINISHED"
        )

    def execDetailsEnd(
        self,
        reqId,
    ):
        self.executions_finished = True

        print(
            "EXECUTIONS DOWNLOAD FINISHED"
        )


def wait_for_flag(
    condition,
    timeout_seconds,
    message,
):
    timeout = (
        time.time()
        + timeout_seconds
    )

    while not condition():

        if time.time() > timeout:
            raise RuntimeError(
                message
            )

        time.sleep(0.1)


def main():

    print("=" * 60)
    print(
        "PAPER EXECUTION INTEGRATION TEST"
    )
    print(
        "REAL ACCOUNT STATE + REAL MARKET DATA"
    )
    print(
        "SIMULATION ONLY - NO IBKR ORDERS"
    )
    print("=" * 60)

    app = IntegrationApp()

    try:

        # =====================================
        # CONNECT TO IBKR
        # =====================================

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

        wait_for_flag(
            lambda:
                app.connected_successfully,
            IBKR_TIMEOUT_SECONDS,
            "Could not connect to IBKR.",
        )

        wait_for_flag(
            lambda:
                bool(
                    app.managed_accounts
                ),
            IBKR_TIMEOUT_SECONDS,
            "No IBKR account detected.",
        )

        account = (
            app.managed_accounts[0]
        )

        # =====================================
        # HARD PAPER SAFETY
        # =====================================

        if not (
            account.upper()
            .startswith("DU")
        ):
            raise RuntimeError(
                "LIVE ACCOUNT BLOCKED."
            )

        print()
        print(
            "PAPER ACCOUNT VERIFIED."
        )

        # =====================================
        # GET POSITIONS
        # =====================================

        print()
        print(
            "Requesting positions..."
        )

        app.reqPositions()

        wait_for_flag(
            lambda:
                app.positions_finished,
            IBKR_TIMEOUT_SECONDS,
            "Positions request timed out.",
        )

        # =====================================
        # GET OPEN ORDERS
        # =====================================

        print()
        print(
            "Requesting open orders..."
        )

        app.reqAllOpenOrders()

        wait_for_flag(
            lambda:
                app.open_orders_finished,
            IBKR_TIMEOUT_SECONDS,
            "Open orders request timed out.",
        )

        # =====================================
        # GET EXECUTIONS
        # =====================================

        print()
        print(
            "Requesting executions..."
        )

        execution_filter = (
            ExecutionFilter()
        )

        execution_filter.acctCode = (
            account
        )

        app.reqExecutions(
            6001,
            execution_filter,
        )

        wait_for_flag(
            lambda:
                app.executions_finished,
            IBKR_TIMEOUT_SECONDS,
            "Executions request timed out.",
        )

        # =====================================
        # FIND AAPL POSITION
        # =====================================

        target_position = None

        for position in app.positions:

            if (
                position[
                    "symbol"
                ].upper()
                == TARGET_SYMBOL
                and abs(
                    position[
                        "position"
                    ]
                ) > 0
            ):
                target_position = (
                    position
                )

                break

        if target_position is None:

            print()
            print(
                f"No open position found "
                f"for {TARGET_SYMBOL}."
            )

            return

        position_size = float(
            target_position[
                "position"
            ]
        )

        if position_size > 0:
            side = "LONG"

        else:
            side = "SHORT"

        quantity = abs(
            position_size
        )

        print()
        print("=" * 60)
        print("CURRENT IBKR POSITION")
        print("=" * 60)

        print(
            f"Symbol: "
            f"{TARGET_SYMBOL}"
        )

        print(
            f"Side: "
            f"{side}"
        )

        print(
            f"Quantity: "
            f"{quantity}"
        )

        print(
            f"IBKR Avg Cost: "
            f"{target_position['avg_cost']:.2f}"
        )

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

            state_matches = (
                stored_side == side
                and abs(
                    stored_quantity
                    - quantity
                ) < 0.000001
            )

        else:

            state_matches = False

        if (
            state_matches
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

            entry_source = str(
                stored_state.get(
                    "entry_price_source",
                    "PERSISTENT STATE",
                )
            )

        else:

            entry_price = float(
                target_position[
                    "avg_cost"
                ]
            )

            entry_source = (
                "IBKR AVG COST FALLBACK"
            )

        print(
            f"Entry price: "
            f"{entry_price:.2f}"
        )

        print(
            f"Entry source: "
            f"{entry_source}"
        )

        # =====================================
        # FIND ACTIVE STOP
        # =====================================

        stop_order = None

        for order in app.open_orders:

            if (
                order[
                    "symbol"
                ].upper()
                == TARGET_SYMBOL
                and order[
                    "order_type"
                ].upper()
                == "STP"
            ):
                stop_order = order

                break

        if stop_order is None:

            current_stop = None

        else:

            current_stop = float(
                stop_order[
                    "stop_price"
                ]
            )

        print(
            f"Current broker stop: "
            f"{current_stop}"
        )

        # =====================================
        # GET MARKET DATA
        # =====================================

        print()
        print(
            "Requesting Alpaca "
            "market data..."
        )

        market_quote = (
            get_current_market_price(
                TARGET_SYMBOL
            )
        )

        current_price = float(
            market_quote[
                "price"
            ]
        )

        timestamp = (
            market_quote[
                "timestamp"
            ]
        )

        print()
        print("=" * 60)
        print("MARKET DATA")
        print("=" * 60)

        print(
            f"Price: "
            f"{current_price:.2f}"
        )

        print(
            f"Timestamp: "
            f"{timestamp}"
        )

        print(
            f"Source: "
            f"{market_quote['source']}"
        )

        # =====================================
        # MARKET DATA GUARD
        # =====================================

        market_guard = (
            MarketDataGuard(
                max_age_seconds=(
                    MARKET_DATA_MAX_AGE_SECONDS
                )
            )
        )

        market_safety = (
            market_guard.evaluate(
                timestamp
            )
        )

        market_data_fresh = bool(
            market_safety[
                "fresh"
            ]
        )

        print()
        print("=" * 60)
        print("MARKET DATA SAFETY")
        print("=" * 60)

        print(
            f"Fresh: "
            f"{market_data_fresh}"
        )

        print(
            f"Age seconds: "
            f"{market_safety['age_seconds']}"
        )

        print(
            f"Reason: "
            f"{market_safety['reason']}"
        )

        # =====================================
        # HIGH / LOW WATER MARK
        # =====================================

        if state_matches:

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

            highest_price = (
                entry_price
            )

            lowest_price = (
                entry_price
            )

        # Only fresh market data may
        # modify persistent water marks.

        if market_data_fresh:

            highest_price = max(
                highest_price,
                current_price,
            )

            lowest_price = min(
                lowest_price,
                current_price,
            )

        # =====================================
        # POSITION MANAGER
        # =====================================

        position_manager = (
            PositionManager()
        )

        if side == "LONG":

            position_result = (
                position_manager
                .calculate_stop(
                    side="LONG",
                    entry_price=(
                        entry_price
                    ),
                    current_price=(
                        current_price
                    ),
                    highest_price=(
                        highest_price
                    ),
                    current_stop=(
                        current_stop
                    ),
                )
            )

        else:

            position_result = (
                position_manager
                .calculate_stop(
                    side="SHORT",
                    entry_price=(
                        entry_price
                    ),
                    current_price=(
                        current_price
                    ),
                    lowest_price=(
                        lowest_price
                    ),
                    current_stop=(
                        current_stop
                    ),
                )
            )

        suggested_stop = float(
            position_result[
                "suggested_stop"
            ]
        )

        print()
        print("=" * 60)
        print("POSITION MANAGER")
        print("=" * 60)

        print(
            f"Stage: "
            f"{position_result['stage']}"
        )

        print(
            f"Current move: "
            f"{position_result['current_move_percent']:.3f}%"
        )

        print(
            f"Favorable move: "
            f"{position_result['favorable_move_percent']:.3f}%"
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
                current_price=(
                    current_price
                ),
                suggested_stop=(
                    suggested_stop
                ),
                current_stop=(
                    current_stop
                ),
            )
        )

        reconciliation_action = (
            reconciliation[
                "action"
            ]
        )

        print()
        print("=" * 60)
        print("RECONCILIATION")
        print("=" * 60)

        print(
            f"Action: "
            f"{reconciliation_action}"
        )

        print(
            f"Reason: "
            f"{reconciliation['reason']}"
        )

        # =====================================
        # PAPER EXECUTION MANAGER
        # =====================================

        execution_manager = (
            PaperExecutionManager()
        )

        execution_plan = (
            execution_manager
            .build_execution_plan(
                account=account,
                symbol=TARGET_SYMBOL,
                side=side,
                quantity=quantity,
                reconciliation_action=(
                    reconciliation_action
                ),
                market_data_fresh=(
                    market_data_fresh
                ),
                current_price=(
                    current_price
                ),
                suggested_stop=(
                    suggested_stop
                ),
                current_stop=(
                    current_stop
                ),
            )
        )

        print()
        print("=" * 60)
        print("PAPER EXECUTION PLAN")
        print("=" * 60)

        print(
            f"Allowed: "
            f"{execution_plan['allowed']}"
        )

        print(
            f"Reason: "
            f"{execution_plan['reason']}"
        )

        print(
            f"IBKR action: "
            f"{execution_plan['ibkr_action']}"
        )

        print(
            f"IBKR order type: "
            f"{execution_plan['ibkr_order_type']}"
        )

        print(
            f"IBKR stop price: "
            f"{execution_plan['ibkr_stop_price']}"
        )

        # =====================================
        # ABSOLUTE SAFETY ASSERTION
        # =====================================

        print()
        print("=" * 60)
        print("FINAL SAFETY STATUS")
        print("=" * 60)

        if execution_plan[
            "allowed"
        ]:

            print(
                "EXECUTION PLAN APPROVED"
            )

            print(
                "BUT THIS TEST DOES NOT "
                "SEND THE ORDER."
            )

        else:

            print(
                "EXECUTION PLAN BLOCKED"
            )

            print(
                f"Reason: "
                f"{execution_plan['reason']}"
            )

        print()
        print(
            "SIMULATION ONLY - "
            "NO placeOrder() WAS CALLED."
        )

    finally:

        if app.isConnected():
            app.disconnect()


if __name__ == "__main__":
    main()