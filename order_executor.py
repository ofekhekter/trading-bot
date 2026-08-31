from ibapi.contract import Contract
from ibapi.order import Order
import time


class OrderExecutor:

    def __init__(self, app):
        self.app = app

    def _get_paper_account(self):

        if not self.app.managed_accounts:
            raise RuntimeError("No IBKR account detected.")

        account = self.app.managed_accounts[0]

        # HARD SAFETY BLOCK:
        # Only allow simulated/paper IBKR accounts
        if not account.upper().startswith("DU"):
            raise RuntimeError(
                "ORDER BLOCKED: Connected account is not recognized as PAPER."
            )

        return account

    def create_stock_contract(self, symbol):

        contract = Contract()

        contract.symbol = symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        return contract

    def place_bracket_order(
        self,
        symbol,
        action,
        quantity,
        stop_price,
        take_profit_price,
    ):

        account = self._get_paper_account()

        if self.app.next_order_id is None:
            raise RuntimeError("No valid IBKR order ID available.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        action = action.upper()

        if action not in ("BUY", "SELL"):
            raise ValueError("Action must be BUY or SELL.")

        contract = self.create_stock_contract(symbol)

        parent_id = self.app.next_order_id
        take_profit_id = parent_id + 1
        stop_id = parent_id + 2

        exit_action = "SELL" if action == "BUY" else "BUY"

        # -------------------------
        # ENTRY ORDER
        # -------------------------

        parent = Order()

        parent.orderId = parent_id
        parent.action = action
        parent.orderType = "MKT"
        parent.totalQuantity = quantity
        parent.transmit = False
        parent.account = account

        # -------------------------
        # TAKE PROFIT
        # -------------------------

        take_profit = Order()

        take_profit.orderId = take_profit_id
        take_profit.action = exit_action
        take_profit.orderType = "LMT"
        take_profit.totalQuantity = quantity
        take_profit.lmtPrice = round(take_profit_price, 2)
        take_profit.parentId = parent_id
        take_profit.transmit = False
        take_profit.account = account

        # -------------------------
        # STOP LOSS
        # -------------------------

        stop_loss = Order()

        stop_loss.orderId = stop_id
        stop_loss.action = exit_action
        stop_loss.orderType = "STP"
        stop_loss.totalQuantity = quantity
        stop_loss.auxPrice = round(stop_price, 2)
        stop_loss.parentId = parent_id
        stop_loss.transmit = True
        stop_loss.account = account

        print("=" * 60)
        print("PAPER BRACKET ORDER")
        print(f"Account: PAPER ({account[:2]}...)")
        print(f"Symbol: {symbol}")
        print(f"Action: {action}")
        print(f"Quantity: {quantity}")
        print(f"Stop Loss: {stop_price:.2f}")
        print(f"Take Profit: {take_profit_price:.2f}")
        print("=" * 60)

        self.app.placeOrder(
            parent_id,
            contract,
            parent,
        )

        self.app.placeOrder(
            take_profit_id,
            contract,
            take_profit,
        )

        self.app.placeOrder(
            stop_id,
            contract,
            stop_loss,
        )

        self.app.next_order_id += 3

        print("Bracket order sent to IBKR PAPER.")