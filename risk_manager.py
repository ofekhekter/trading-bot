class RiskManager:
    def __init__(
        self,
        max_capital: float,
        max_position: float,
        stop_loss_pct: float = 1.0,
        take_profit_pct: float = 2.0,
    ):
        self.max_capital = max_capital
        self.max_position = max_position
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.used_capital = 0.0

    def can_open_position(self, amount: float) -> tuple[bool, str]:
        if amount <= 0:
            return False, "Trade amount must be greater than $0."

        if amount > self.max_position:
            return False, (
                f"Trade rejected: ${amount:,.2f} exceeds "
                f"max position size of ${self.max_position:,.2f}."
            )

        if self.used_capital + amount > self.max_capital:
            return False, (
                f"Trade rejected: total exposure would exceed "
                f"${self.max_capital:,.2f}."
            )

        return True, "Trade approved."

    def calculate_trade_plan(
        self,
        action: str,
        price: float,
        trade_amount: float,
    ) -> dict:

        if price <= 0:
            raise ValueError("Price must be greater than zero.")

        approved, reason = self.can_open_position(trade_amount)

        if not approved:
            return {
                "approved": False,
                "reason": reason,
            }

        quantity = int(trade_amount // price)

        if quantity <= 0:
            return {
                "approved": False,
                "reason": (
                    f"Trade amount ${trade_amount:.2f} is too small "
                    f"for price ${price:.2f}."
                ),
            }

        actual_amount = quantity * price

        action = action.upper()

        if action == "LONG":
            stop_price = price * (1 - self.stop_loss_pct / 100)
            take_profit_price = price * (
                1 + self.take_profit_pct / 100
            )
            order_action = "BUY"

        elif action == "SHORT":
            stop_price = price * (1 + self.stop_loss_pct / 100)
            take_profit_price = price * (
                1 - self.take_profit_pct / 100
            )
            order_action = "SELL"

        else:
            return {
                "approved": False,
                "reason": f"Unsupported action: {action}",
            }

        return {
            "approved": True,
            "reason": "Trade approved.",
            "order_action": order_action,
            "quantity": quantity,
            "entry_price": round(price, 2),
            "stop_price": round(stop_price, 2),
            "take_profit_price": round(take_profit_price, 2),
            "position_value": round(actual_amount, 2),
        }

    def register_position(self, amount: float):
        self.used_capital += amount

    def release_position(self, amount: float):
        self.used_capital = max(
            0.0,
            self.used_capital - amount
        )