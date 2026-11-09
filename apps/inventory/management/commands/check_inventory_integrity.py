from django.core.management.base import BaseCommand, CommandError

from apps.inventory.integrity_services import (
    check_inventory_balance_integrity,
)


class Command(BaseCommand):
    help = "Compare inventory balances with the stock movement ledger."

    def handle(self, *args, **options):
        try:
            discrepancies = check_inventory_balance_integrity()
        except Exception as exc:
            raise CommandError(
                f"Inventory integrity check failed: {exc}"
            ) from exc

        if not discrepancies:
            self.stdout.write(
                self.style.SUCCESS(
                    "Inventory integrity check passed. "
                    "No discrepancies detected."
                )
            )
            return

        self.stdout.write(
            self.style.ERROR(
                f"Detected {len(discrepancies)} stock discrepancies."
            )
        )

        for item in discrepancies:
            self.stdout.write(
                f"Batch: {item['batch_number']} | "
                f"Medicine: {item['medicine']} | "
                f"Warehouse: {item['warehouse']} | "
                f"Balance: {item['balance_quantity']} | "
                f"Ledger: {item['ledger_quantity']} | "
                f"Difference: {item['discrepancy']}"
            )

        raise CommandError(
            "Inventory integrity check found discrepancies."
        )