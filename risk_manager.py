class RiskManager:
    def __init__(self, max_capital: float, max_position: float):
        self.max_capital = max_capital
        self.max_position = max_position
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

    def register_position(self, amount: float):
        self.used_capital += amount

    def release_position(self, amount: float):
        self.used_capital = max(0.0, self.used_capital - amount)