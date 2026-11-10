from django.core.exceptions import ImproperlyConfigured


def post_received_stock(
    *,
    receiving_line,
    quantity,
    receiving_warehouse,
    user,
    receiving_record,
):
    """
    Integrate with the actual Phase 15 inventory receipt service.

    Requirements:
      1. Create or identify a recipient-side stock batch.
      2. Preserve the original manufacturer batch number.
      3. Preserve expiry and manufacture dates.
      4. Add accepted quantity to recipient stock.
      5. Create an immutable inbound StockMovement.
      6. Execute inside the caller's transaction.
      7. Be idempotent: a receiving line must not be posted twice.

    Do not directly update InventoryBalance here.
    """

    raise ImproperlyConfigured(
        "Recipient inventory posting is not configured. "
        "Connect this adapter to the Phase 15 stock receipt "
        "service before posting receiving records."
    )