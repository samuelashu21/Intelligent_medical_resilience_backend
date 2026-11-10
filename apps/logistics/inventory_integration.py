from django.core.exceptions import ImproperlyConfigured


def post_reserved_dispatch(
    *,
    transfer_line,
    quantity,
    user,
    shipment,
):
    """
    Inventory integration boundary.

    Connect this function to the actual Phase 15 inventory
    movement service. It must:

    - Decrease quantity_on_hand.
    - Decrease quantity_reserved.
    - Create the immutable outbound StockMovement.
    - Validate the batch and donor warehouse.
    - Execute within the caller's database transaction.

    It must not issue stock a second time or decrement
    reserved quantities twice.
    """

    raise ImproperlyConfigured(
        "Dispatch integration is not configured. Connect "
        "post_reserved_dispatch() to the actual Phase 15 "
        "inventory stock-movement service before enabling dispatch."
    )