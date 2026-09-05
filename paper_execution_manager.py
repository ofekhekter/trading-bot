class PaperExecutionManager:
    """
    Safety layer between the trading logic and IBKR PAPER execution.

    IMPORTANT:
    This version is SIMULATION ONLY.
    It does NOT call IBKR placeOrder().
    """

    ALLOWED_ACTIONS = {
        "NO_ACTION",
        "CREATE_STOP_REQUIRED",
        "RAISE_STOP",
        "LOWER_STOP",
        "EXIT_REQUIRED",
    }

    def __init__(self):
        self.last_plan = None

    @staticmethod
    def _verify_paper_account(account):
        if not account:
            return False, "IBKR_ACCOUNT_MISSING"

        if not str(account).upper().startswith("DU"):
            return False, "LIVE_ACCOUNT_BLOCKED"

        return True, "PAPER_ACCOUNT_VERIFIED"

    @staticmethod
    def _verify_market_data(market_data_fresh):
        if market_data_fresh is not True:
            return False, "MARKET_DATA_NOT_FRESH"

        return True, "MARKET_DATA_VERIFIED"

    @staticmethod
    def _verify_position(side, quantity):
        side = str(side).upper()

        if side not in ("LONG", "SHORT"):
            return False, "INVALID_POSITION_SIDE"

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            return False, "INVALID_POSITION_QUANTITY"

        if quantity <= 0:
            return False, "POSITION_QUANTITY_NOT_POSITIVE"

        return True, "POSITION_VERIFIED"

    @staticmethod
    def _verify_price(price, name):
        if price is None:
            return False, f"{name}_MISSING"

        try:
            price = float(price)
        except (TypeError, ValueError):
            return False, f"{name}_INVALID"

        if price <= 0:
            return False, f"{name}_NOT_POSITIVE"

        return True, f"{name}_VERIFIED"

    def build_execution_plan(
        self,
        *,
        account,
        symbol,
        side,
        quantity,
        reconciliation_action,
        market_data_fresh,
        current_price,
        suggested_stop=None,
        current_stop=None,
    ):
        """
        Build a safe PAPER execution plan.

        NO IBKR order is sent from this method.
        """

        action = str(
            reconciliation_action
        ).upper()

        symbol = str(symbol).upper().strip()
        side = str(side).upper().strip()

        result = {
            "allowed": False,
            "reason": None,
            "account": account,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "reconciliation_action": action,
            "market_data_fresh": market_data_fresh,
            "current_price": current_price,
            "current_stop": current_stop,
            "suggested_stop": suggested_stop,
            "ibkr_action": None,
            "ibkr_order_type": None,
            "ibkr_stop_price": None,
        }

        # -------------------------------------------------
        # ACTION VALIDATION
        # -------------------------------------------------

        if action not in self.ALLOWED_ACTIONS:
            result["reason"] = (
                "UNKNOWN_RECONCILIATION_ACTION"
            )
            return result

        # -------------------------------------------------
        # NO ACTION
        # -------------------------------------------------

        if action == "NO_ACTION":
            result["reason"] = "NO_ACTION_REQUIRED"
            self.last_plan = result
            return result

        # -------------------------------------------------
        # PAPER ACCOUNT SAFETY
        # -------------------------------------------------

        valid, reason = (
            self._verify_paper_account(
                account
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        # -------------------------------------------------
        # MARKET DATA SAFETY
        # -------------------------------------------------

        valid, reason = (
            self._verify_market_data(
                market_data_fresh
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        # -------------------------------------------------
        # SYMBOL SAFETY
        # -------------------------------------------------

        if not symbol:
            result["reason"] = "SYMBOL_MISSING"
            return result

        # -------------------------------------------------
        # POSITION SAFETY
        # -------------------------------------------------

        valid, reason = (
            self._verify_position(
                side,
                quantity,
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        quantity = float(quantity)

        result["quantity"] = quantity

        # -------------------------------------------------
        # CURRENT MARKET PRICE SAFETY
        # -------------------------------------------------

        valid, reason = (
            self._verify_price(
                current_price,
                "CURRENT_PRICE",
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        current_price = float(
            current_price
        )

        result["current_price"] = (
            current_price
        )

        # -------------------------------------------------
        # EXIT POSITION
        # -------------------------------------------------

        if action == "EXIT_REQUIRED":

            if side == "LONG":
                ibkr_action = "SELL"
            else:
                ibkr_action = "BUY"

            result.update(
                {
                    "allowed": True,
                    "reason": "EXIT_PLAN_APPROVED",
                    "ibkr_action": ibkr_action,
                    "ibkr_order_type": "MKT",
                    "ibkr_stop_price": None,
                }
            )

            self.last_plan = result

            return result

        # -------------------------------------------------
        # STOP ACTIONS REQUIRE A VALID STOP PRICE
        # -------------------------------------------------

        valid, reason = (
            self._verify_price(
                suggested_stop,
                "SUGGESTED_STOP",
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        suggested_stop = float(
            suggested_stop
        )

        result["suggested_stop"] = (
            suggested_stop
        )

        # -------------------------------------------------
        # PROTECT AGAINST CREATING A STOP
        # THAT HAS ALREADY BEEN CROSSED
        # -------------------------------------------------

        if side == "LONG":

            if current_price <= suggested_stop:
                result["reason"] = (
                    "LONG_STOP_ALREADY_CROSSED"
                )
                return result

            ibkr_action = "SELL"

        else:

            if current_price >= suggested_stop:
                result["reason"] = (
                    "SHORT_STOP_ALREADY_CROSSED"
                )
                return result

            ibkr_action = "BUY"

        # -------------------------------------------------
        # CREATE NEW STOP
        # -------------------------------------------------

        if action == "CREATE_STOP_REQUIRED":

            if current_stop is not None:
                result["reason"] = (
                    "CREATE_STOP_BLOCKED_"
                    "CURRENT_STOP_ALREADY_EXISTS"
                )
                return result

            result.update(
                {
                    "allowed": True,
                    "reason": (
                        "CREATE_STOP_PLAN_APPROVED"
                    ),
                    "ibkr_action": ibkr_action,
                    "ibkr_order_type": "STP",
                    "ibkr_stop_price": round(
                        suggested_stop,
                        2,
                    ),
                }
            )

            self.last_plan = result

            return result

        # -------------------------------------------------
        # MODIFY EXISTING STOP
        # -------------------------------------------------

        valid, reason = (
            self._verify_price(
                current_stop,
                "CURRENT_STOP",
            )
        )

        if not valid:
            result["reason"] = reason
            return result

        current_stop = float(
            current_stop
        )

        result["current_stop"] = (
            current_stop
        )

        # -------------------------------------------------
        # LONG:
        # STOP MAY ONLY MOVE UP
        # -------------------------------------------------

        if action == "RAISE_STOP":

            if side != "LONG":
                result["reason"] = (
                    "RAISE_STOP_REQUIRES_LONG"
                )
                return result

            if suggested_stop <= current_stop:
                result["reason"] = (
                    "RAISE_STOP_NOT_AN_IMPROVEMENT"
                )
                return result

            result.update(
                {
                    "allowed": True,
                    "reason": (
                        "RAISE_STOP_PLAN_APPROVED"
                    ),
                    "ibkr_action": "SELL",
                    "ibkr_order_type": "STP",
                    "ibkr_stop_price": round(
                        suggested_stop,
                        2,
                    ),
                }
            )

            self.last_plan = result

            return result

        # -------------------------------------------------
        # SHORT:
        # STOP MAY ONLY MOVE DOWN
        # -------------------------------------------------

        if action == "LOWER_STOP":

            if side != "SHORT":
                result["reason"] = (
                    "LOWER_STOP_REQUIRES_SHORT"
                )
                return result

            if suggested_stop >= current_stop:
                result["reason"] = (
                    "LOWER_STOP_NOT_AN_IMPROVEMENT"
                )
                return result

            result.update(
                {
                    "allowed": True,
                    "reason": (
                        "LOWER_STOP_PLAN_APPROVED"
                    ),
                    "ibkr_action": "BUY",
                    "ibkr_order_type": "STP",
                    "ibkr_stop_price": round(
                        suggested_stop,
                        2,
                    ),
                }
            )

            self.last_plan = result

            return result

        result["reason"] = (
            "ACTION_NOT_HANDLED"
        )

        return result


def print_plan(name, plan):
    print("-" * 60)
    print(name)
    print("-" * 60)

    print(
        f"Allowed: {plan['allowed']}"
    )

    print(
        f"Reason: {plan['reason']}"
    )

    print(
        f"Action: "
        f"{plan['reconciliation_action']}"
    )

    print(
        f"Symbol: {plan['symbol']}"
    )

    print(
        f"Side: {plan['side']}"
    )

    print(
        f"Quantity: {plan['quantity']}"
    )

    print(
        f"IBKR action: "
        f"{plan['ibkr_action']}"
    )

    print(
        f"IBKR order type: "
        f"{plan['ibkr_order_type']}"
    )

    print(
        f"IBKR stop price: "
        f"{plan['ibkr_stop_price']}"
    )


if __name__ == "__main__":

    manager = PaperExecutionManager()

    print("=" * 60)
    print("PAPER EXECUTION MANAGER TEST")
    print("SIMULATION ONLY - NO IBKR ORDERS")
    print("=" * 60)

    # -------------------------------------------------
    # TEST 1
    # LONG - CREATE STOP
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "CREATE_STOP_REQUIRED"
        ),
        market_data_fresh=True,
        current_price=330.00,
        suggested_stop=322.78,
        current_stop=None,
    )

    print_plan(
        "TEST 1 - LONG CREATE STOP",
        plan,
    )

    # -------------------------------------------------
    # TEST 2
    # LONG - RAISE STOP
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "RAISE_STOP"
        ),
        market_data_fresh=True,
        current_price=330.00,
        suggested_stop=325.00,
        current_stop=323.00,
    )

    print_plan(
        "TEST 2 - LONG RAISE STOP",
        plan,
    )

    # -------------------------------------------------
    # TEST 3
    # SHORT - LOWER STOP
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="SHORT",
        quantity=1,
        reconciliation_action=(
            "LOWER_STOP"
        ),
        market_data_fresh=True,
        current_price=310.00,
        suggested_stop=314.00,
        current_stop=316.00,
    )

    print_plan(
        "TEST 3 - SHORT LOWER STOP",
        plan,
    )

    # -------------------------------------------------
    # TEST 4
    # EXIT LONG
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "EXIT_REQUIRED"
        ),
        market_data_fresh=True,
        current_price=319.80,
        suggested_stop=322.78,
        current_stop=None,
    )

    print_plan(
        "TEST 4 - LONG EXIT",
        plan,
    )

    # -------------------------------------------------
    # TEST 5
    # STALE MARKET DATA MUST BLOCK
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "EXIT_REQUIRED"
        ),
        market_data_fresh=False,
        current_price=319.80,
        suggested_stop=322.78,
        current_stop=None,
    )

    print_plan(
        "TEST 5 - STALE DATA BLOCK",
        plan,
    )

    # -------------------------------------------------
    # TEST 6
    # LIVE ACCOUNT MUST BLOCK
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="U1234567",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "EXIT_REQUIRED"
        ),
        market_data_fresh=True,
        current_price=319.80,
        suggested_stop=322.78,
        current_stop=None,
    )

    print_plan(
        "TEST 6 - LIVE ACCOUNT BLOCK",
        plan,
    )

    # -------------------------------------------------
    # TEST 7
    # CROSSED LONG STOP MUST BLOCK
    # -------------------------------------------------

    plan = manager.build_execution_plan(
        account="DU_TEST_ACCOUNT",
        symbol="AAPL",
        side="LONG",
        quantity=1,
        reconciliation_action=(
            "CREATE_STOP_REQUIRED"
        ),
        market_data_fresh=True,
        current_price=319.80,
        suggested_stop=322.78,
        current_stop=None,
    )

    print_plan(
        "TEST 7 - CROSSED STOP BLOCK",
        plan,
    )

    print("=" * 60)
    print("TEST FINISHED")
    print("NO ORDER WAS SENT TO IBKR.")
    print("=" * 60)