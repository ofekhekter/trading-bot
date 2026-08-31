from position_manager import PositionManager


manager = PositionManager()

entry = 100.00

test_prices = [
    100.00,
    99.60,
    99.10,
    98.60,
    97.50,
]

lowest = entry
current_stop = 101.00


print("=" * 60)
print("SHORT POSITION MANAGER DRY RUN")
print("=" * 60)


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

    new_stop = result[
        "suggested_stop"
    ]

    print(
        f"Price={price:.2f} | "
        f"Move={result['move_percent']:.3f}% | "
        f"Stage={result['stage']} | "
        f"Stop={new_stop:.2f}"
    )

    current_stop = min(
        current_stop,
        new_stop,
    )