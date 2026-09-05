class PositionManager:

    def __init__(
        self,
        initial_stop_percent=1.0,
        break_even_trigger_percent=0.7,
        profit_lock_trigger_percent=1.2,
        profit_lock_percent=0.4,
        trailing_trigger_percent=2.0,
        trailing_distance_percent=0.8,
    ):
        self.initial_stop_percent = initial_stop_percent
        self.break_even_trigger_percent = (
            break_even_trigger_percent
        )
        self.profit_lock_trigger_percent = (
            profit_lock_trigger_percent
        )
        self.profit_lock_percent = (
            profit_lock_percent
        )
        self.trailing_trigger_percent = (
            trailing_trigger_percent
        )
        self.trailing_distance_percent = (
            trailing_distance_percent
        )

    def calculate_stop(
        self,
        side,
        entry_price,
        current_price,
        highest_price=None,
        lowest_price=None,
        current_stop=None,
    ):
        side = side.upper()

        if side not in (
            "LONG",
            "SHORT",
        ):
            raise ValueError(
                "side must be LONG or SHORT"
            )

        if entry_price <= 0:
            raise ValueError(
                "entry_price must be greater than zero"
            )

        if current_price <= 0:
            raise ValueError(
                "current_price must be greater than zero"
            )

        if side == "LONG":
            return self._calculate_long_stop(
                entry_price=entry_price,
                current_price=current_price,
                highest_price=highest_price,
                current_stop=current_stop,
            )

        return self._calculate_short_stop(
            entry_price=entry_price,
            current_price=current_price,
            lowest_price=lowest_price,
            current_stop=current_stop,
        )

    def _calculate_long_stop(
        self,
        entry_price,
        current_price,
        highest_price,
        current_stop,
    ):
        if highest_price is None:
            highest_price = current_price

        highest_price = max(
            highest_price,
            current_price,
        )

        current_move_percent = (
            (current_price - entry_price)
            / entry_price
        ) * 100

        favorable_move_percent = (
            (highest_price - entry_price)
            / entry_price
        ) * 100

        initial_stop = entry_price * (
            1
            - self.initial_stop_percent / 100
        )

        suggested_stop = initial_stop
        stage = "INITIAL_STOP"

        if (
            favorable_move_percent
            >= self.break_even_trigger_percent
        ):
            suggested_stop = entry_price
            stage = "BREAK_EVEN"

        if (
            favorable_move_percent
            >= self.profit_lock_trigger_percent
        ):
            suggested_stop = entry_price * (
                1
                + self.profit_lock_percent / 100
            )

            stage = "PROFIT_LOCK"

        if (
            favorable_move_percent
            >= self.trailing_trigger_percent
        ):
            trailing_stop = highest_price * (
                1
                - self.trailing_distance_percent / 100
            )

            suggested_stop = max(
                suggested_stop,
                trailing_stop,
            )

            stage = "TRAILING"

        if current_stop is not None:
            suggested_stop = max(
                suggested_stop,
                current_stop,
            )

        return {
            "side": "LONG",
            "entry_price": round(
                entry_price,
                2,
            ),
            "current_price": round(
                current_price,
                2,
            ),
            "highest_price": round(
                highest_price,
                2,
            ),
            "current_move_percent": round(
                current_move_percent,
                3,
            ),
            "favorable_move_percent": round(
                favorable_move_percent,
                3,
            ),
            "stage": stage,
            "suggested_stop": round(
                suggested_stop,
                2,
            ),
            "current_stop": (
                round(
                    current_stop,
                    2,
                )
                if current_stop is not None
                else None
            ),
        }

    def _calculate_short_stop(
        self,
        entry_price,
        current_price,
        lowest_price,
        current_stop,
    ):
        if lowest_price is None:
            lowest_price = current_price

        lowest_price = min(
            lowest_price,
            current_price,
        )

        current_move_percent = (
            (entry_price - current_price)
            / entry_price
        ) * 100

        favorable_move_percent = (
            (entry_price - lowest_price)
            / entry_price
        ) * 100

        initial_stop = entry_price * (
            1
            + self.initial_stop_percent / 100
        )

        suggested_stop = initial_stop
        stage = "INITIAL_STOP"

        if (
            favorable_move_percent
            >= self.break_even_trigger_percent
        ):
            suggested_stop = entry_price
            stage = "BREAK_EVEN"

        if (
            favorable_move_percent
            >= self.profit_lock_trigger_percent
        ):
            suggested_stop = entry_price * (
                1
                - self.profit_lock_percent / 100
            )

            stage = "PROFIT_LOCK"

        if (
            favorable_move_percent
            >= self.trailing_trigger_percent
        ):
            trailing_stop = lowest_price * (
                1
                + self.trailing_distance_percent / 100
            )

            suggested_stop = min(
                suggested_stop,
                trailing_stop,
            )

            stage = "TRAILING"

        if current_stop is not None:
            suggested_stop = min(
                suggested_stop,
                current_stop,
            )

        return {
            "side": "SHORT",
            "entry_price": round(
                entry_price,
                2,
            ),
            "current_price": round(
                current_price,
                2,
            ),
            "lowest_price": round(
                lowest_price,
                2,
            ),
            "current_move_percent": round(
                current_move_percent,
                3,
            ),
            "favorable_move_percent": round(
                favorable_move_percent,
                3,
            ),
            "stage": stage,
            "suggested_stop": round(
                suggested_stop,
                2,
            ),
            "current_stop": (
                round(
                    current_stop,
                    2,
                )
                if current_stop is not None
                else None
            ),
        }


if __name__ == "__main__":

    manager = PositionManager()

    print("=" * 60)
    print("POSITION MANAGER LONG TEST")
    print("=" * 60)

    entry = 315.86

    test_prices = [
        315.86,
        317.00,
        318.50,
        320.00,
        323.00,
        319.00,
    ]

    highest = entry
    current_stop = 312.70

    for price in test_prices:

        highest = max(
            highest,
            price,
        )

        result = manager.calculate_stop(
            side="LONG",
            entry_price=entry,
            current_price=price,
            highest_price=highest,
            current_stop=current_stop,
        )

        new_stop = (
            result["suggested_stop"]
        )

        print(
            f"Price={price:.2f} | "
            f"Current={result['current_move_percent']:.3f}% | "
            f"Favorable={result['favorable_move_percent']:.3f}% | "
            f"Stage={result['stage']} | "
            f"Stop={new_stop:.2f}"
        )

        current_stop = max(
            current_stop,
            new_stop,
        )

    print()
    print("=" * 60)
    print("POSITION MANAGER SHORT TEST")
    print("=" * 60)

    entry = 315.86

    test_prices = [
        315.86,
        314.00,
        312.50,
        310.00,
        307.00,
        311.00,
    ]

    lowest = entry
    current_stop = 319.02

    for price in test_prices:

        lowest = min(
            lowest,
            price,
        )

        result = manager.calculate_stop(
            side="SHORT",
            entry_price=entry,
            current_price=price,
            lowest_price=lowest,
            current_stop=current_stop,
        )

        new_stop = (
            result["suggested_stop"]
        )

        print(
            f"Price={price:.2f} | "
            f"Current={result['current_move_percent']:.3f}% | "
            f"Favorable={result['favorable_move_percent']:.3f}% | "
            f"Stage={result['stage']} | "
            f"Stop={new_stop:.2f}"
        )

        current_stop = min(
            current_stop,
            new_stop,
        )