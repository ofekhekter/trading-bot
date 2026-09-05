class PositionReconciler:

    def evaluate(
        self,
        side,
        current_price,
        suggested_stop,
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

        if current_price <= 0:
            raise ValueError(
                "current_price must be greater than zero"
            )

        if suggested_stop <= 0:
            raise ValueError(
                "suggested_stop must be greater than zero"
            )

        if (
            current_stop is not None
            and current_stop <= 0
        ):
            raise ValueError(
                "current_stop must be greater than zero"
            )

        if side == "LONG":
            return self._evaluate_long(
                current_price=current_price,
                suggested_stop=suggested_stop,
                current_stop=current_stop,
            )

        return self._evaluate_short(
            current_price=current_price,
            suggested_stop=suggested_stop,
            current_stop=current_stop,
        )

    def _evaluate_long(
        self,
        current_price,
        suggested_stop,
        current_stop,
    ):
        if current_price <= suggested_stop:
            return {
                "action": "EXIT_REQUIRED",
                "reason": (
                    "LONG position is already "
                    "at or below the required "
                    "protective stop."
                ),
                "side": "LONG",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": (
                    round(
                        current_stop,
                        2,
                    )
                    if current_stop
                    is not None
                    else None
                ),
            }

        if current_stop is None:
            return {
                "action": "CREATE_STOP_REQUIRED",
                "reason": (
                    "LONG position has no active "
                    "protective stop."
                ),
                "side": "LONG",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": None,
            }

        if suggested_stop > current_stop:
            return {
                "action": "RAISE_STOP",
                "reason": (
                    "LONG protective stop can be "
                    "raised without loosening risk."
                ),
                "side": "LONG",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": round(
                    current_stop,
                    2,
                ),
            }

        return {
            "action": "NO_ACTION",
            "reason": (
                "Current LONG stop is already "
                "at or above the required level."
            ),
            "side": "LONG",
            "current_price": round(
                current_price,
                2,
            ),
            "suggested_stop": round(
                suggested_stop,
                2,
            ),
            "current_stop": round(
                current_stop,
                2,
            ),
        }

    def _evaluate_short(
        self,
        current_price,
        suggested_stop,
        current_stop,
    ):
        if current_price >= suggested_stop:
            return {
                "action": "EXIT_REQUIRED",
                "reason": (
                    "SHORT position is already "
                    "at or above the required "
                    "protective stop."
                ),
                "side": "SHORT",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": (
                    round(
                        current_stop,
                        2,
                    )
                    if current_stop
                    is not None
                    else None
                ),
            }

        if current_stop is None:
            return {
                "action": "CREATE_STOP_REQUIRED",
                "reason": (
                    "SHORT position has no active "
                    "protective stop."
                ),
                "side": "SHORT",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": None,
            }

        if suggested_stop < current_stop:
            return {
                "action": "LOWER_STOP",
                "reason": (
                    "SHORT protective stop can be "
                    "lowered without loosening risk."
                ),
                "side": "SHORT",
                "current_price": round(
                    current_price,
                    2,
                ),
                "suggested_stop": round(
                    suggested_stop,
                    2,
                ),
                "current_stop": round(
                    current_stop,
                    2,
                ),
            }

        return {
            "action": "NO_ACTION",
            "reason": (
                "Current SHORT stop is already "
                "at or below the required level."
            ),
            "side": "SHORT",
            "current_price": round(
                current_price,
                2,
            ),
            "suggested_stop": round(
                suggested_stop,
                2,
            ),
            "current_stop": round(
                current_stop,
                2,
            ),
        }


if __name__ == "__main__":

    reconciler = PositionReconciler()

    print("=" * 60)
    print("POSITION RECONCILER LONG TEST")
    print("=" * 60)

    long_cases = [
        {
            "current_price": 319.80,
            "suggested_stop": 322.78,
            "current_stop": None,
        },
        {
            "current_price": 330.00,
            "suggested_stop": 322.78,
            "current_stop": None,
        },
        {
            "current_price": 330.00,
            "suggested_stop": 325.00,
            "current_stop": 323.00,
        },
        {
            "current_price": 330.00,
            "suggested_stop": 323.00,
            "current_stop": 325.00,
        },
    ]

    for case in long_cases:
        result = reconciler.evaluate(
            side="LONG",
            current_price=case["current_price"],
            suggested_stop=case["suggested_stop"],
            current_stop=case["current_stop"],
        )

        print(
            f"Price={case['current_price']:.2f} | "
            f"Suggested={case['suggested_stop']:.2f} | "
            f"CurrentStop={case['current_stop']} | "
            f"Action={result['action']}"
        )

    print()

    print("=" * 60)
    print("POSITION RECONCILER SHORT TEST")
    print("=" * 60)

    short_cases = [
        {
            "current_price": 322.00,
            "suggested_stop": 319.00,
            "current_stop": None,
        },
        {
            "current_price": 310.00,
            "suggested_stop": 319.00,
            "current_stop": None,
        },
        {
            "current_price": 310.00,
            "suggested_stop": 314.00,
            "current_stop": 316.00,
        },
        {
            "current_price": 310.00,
            "suggested_stop": 316.00,
            "current_stop": 314.00,
        },
    ]

    for case in short_cases:
        result = reconciler.evaluate(
            side="SHORT",
            current_price=case["current_price"],
            suggested_stop=case["suggested_stop"],
            current_stop=case["current_stop"],
        )

        print(
            f"Price={case['current_price']:.2f} | "
            f"Suggested={case['suggested_stop']:.2f} | "
            f"CurrentStop={case['current_stop']} | "
            f"Action={result['action']}"
        )