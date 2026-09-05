from datetime import datetime, timezone


class MarketDataGuard:

    def __init__(
        self,
        max_age_seconds=30,
    ):
        self.max_age_seconds = (
            max_age_seconds
        )

    def evaluate(
        self,
        timestamp,
    ):
        if timestamp is None:
            return {
                "fresh": False,
                "age_seconds": None,
                "reason": (
                    "MARKET_DATA_TIMESTAMP_MISSING"
                ),
            }

        if isinstance(
            timestamp,
            str,
        ):
            try:
                timestamp = (
                    datetime.fromisoformat(
                        timestamp.replace(
                            "Z",
                            "+00:00",
                        )
                    )
                )

            except ValueError:
                return {
                    "fresh": False,
                    "age_seconds": None,
                    "reason": (
                        "MARKET_DATA_TIMESTAMP_INVALID"
                    ),
                }

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        age_seconds = (
            now
            - timestamp.astimezone(
                timezone.utc
            )
        ).total_seconds()

        # A timestamp materially in the future
        # should never be trusted.
        if age_seconds < -5:
            return {
                "fresh": False,
                "age_seconds": round(
                    age_seconds,
                    3,
                ),
                "reason": (
                    "MARKET_DATA_TIMESTAMP_IN_FUTURE"
                ),
            }

        # Allow a tiny amount of clock skew.
        age_seconds = max(
            age_seconds,
            0.0,
        )

        if (
            age_seconds
            > self.max_age_seconds
        ):
            return {
                "fresh": False,
                "age_seconds": round(
                    age_seconds,
                    3,
                ),
                "reason": (
                    "MARKET_DATA_STALE"
                ),
            }

        return {
            "fresh": True,
            "age_seconds": round(
                age_seconds,
                3,
            ),
            "reason": (
                "MARKET_DATA_FRESH"
            ),
        }


if __name__ == "__main__":

    from datetime import timedelta

    guard = MarketDataGuard(
        max_age_seconds=30
    )

    print("=" * 60)
    print("MARKET DATA FRESHNESS GUARD TEST")
    print("=" * 60)

    now = datetime.now(
        timezone.utc
    )

    test_cases = [
        (
            "FRESH_1_SECOND",
            now - timedelta(
                seconds=1
            ),
        ),
        (
            "FRESH_20_SECONDS",
            now - timedelta(
                seconds=20
            ),
        ),
        (
            "STALE_31_SECONDS",
            now - timedelta(
                seconds=31
            ),
        ),
        (
            "STALE_5_MINUTES",
            now - timedelta(
                minutes=5
            ),
        ),
        (
            "MISSING_TIMESTAMP",
            None,
        ),
        (
            "FUTURE_TIMESTAMP",
            now + timedelta(
                minutes=5
            ),
        ),
    ]

    for name, timestamp in test_cases:

        result = guard.evaluate(
            timestamp
        )

        print(
            f"{name:<22} | "
            f"Fresh={result['fresh']} | "
            f"Age={result['age_seconds']} | "
            f"Reason={result['reason']}"
        )