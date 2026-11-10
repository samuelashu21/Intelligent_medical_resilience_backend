from decimal import Decimal

from django.db.models import Sum

from apps.inventory.models import (
    InventoryBalance,
    MovementType,
    StockMovement,
)

MOVEMENT_SIGN = {
    MovementType.RECEIPT: Decimal("1"),
    MovementType.ISSUE: Decimal("-1"),
    MovementType.ADJUSTMENT_IN: Decimal("1"),
    MovementType.ADJUSTMENT_OUT: Decimal("-1"),
}


def calculate_ledger_balance(batch_id):
    movements = StockMovement.objects.filter(batch_id=batch_id)

    total = Decimal("0")

    for movement in movements:
        sign = MOVEMENT_SIGN.get(movement.movement_type)

        if sign is None:
            continue

        total += movement.quantity * sign

    return total


def check_inventory_balance_integrity():
    results = []

    balances = InventoryBalance.objects.select_related(
        "batch",
        "batch__medicine",
        "batch__warehouse",
    )

    for balance in balances.iterator():
        ledger_quantity = calculate_ledger_balance(balance.batch_id)

        discrepancy = balance.quantity_on_hand - ledger_quantity

        if discrepancy != 0:
            results.append(
                {
                    "batch_id": str(balance.batch_id),
                    "batch_number": balance.batch.batch_number,
                    "medicine": balance.batch.medicine.generic_name,
                    "warehouse": balance.batch.warehouse.name,
                    "balance_quantity": str(balance.quantity_on_hand),
                    "ledger_quantity": str(ledger_quantity),
                    "discrepancy": str(discrepancy),
                }
            )

    return results
