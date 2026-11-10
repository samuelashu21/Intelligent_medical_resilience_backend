
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Q

from apps.accounts.models import Role, AccessPermission


# ==========================================================
# PERMISSION CATALOG
# ==========================================================

PERMISSIONS = {
    "users": [
        ("view", "View users"),
        ("create", "Create users"),
        ("update", "Update users"),
        ("deactivate", "Deactivate users"),
        ("assign_roles", "Assign user roles"),
    ],
    "organizations": [
        ("view", "View organizations"),
        ("create", "Create organizations"),
        ("update", "Update organizations"),
    ],
    "facilities": [
        ("view", "View facilities"),
        ("create", "Create facilities"),
        ("update", "Update facilities"),
    ],
    "medicines": [
        ("view", "View medicines"),
        ("create", "Create medicines"),
        ("update", "Update medicines"),
    ],
    "inventory": [
        ("view", "View Inventory"),
        ("receive", "Receive stock"),
        ("issue", "Issue stock"),
        ("adjust", "Adjust stock"),
        ("reconcile", "Reconcile Inventory"),
        ("policy.view", "View Stock Policies"),
        ("policy.create", "Create Stock Policies"),
        ("policy.update", "Update Stock Policies"),
        ("policy.manage", "Activate and Deactivate Stock Policies"),
        ("visibility.view", "View Inter-Facility Stock"),
    ],
    "consumption": [
        ("view", "View Medicine Consumption"),
        ("create", "Record Medicine Consumption"),
        ("submit", "Submit Consumption Reports"),
        ("approve", "Approve Consumption Reports"),
    ],
    "replenishment": [
        ("view", "View Replenishment Requests"),
        ("create", "Create Replenishment Requests"),
        ("submit", "Submit Replenishment Requests"),
        ("approve", "Approve Replenishment Requests"),
        ("cancel", "Cancel Replenishment Requests"),
        ("workflow.view", "View Approval Workflows"),
        ("approval.view", "View Approval Stages and Decisions"),
        ("workflow.manage", "Manage Approval Workflows"),
        ("approval.escalate", "Escalate Approval Stages"),
    ],
    "procurement": [
        ("view", "View procurement"),
        ("create", "Create purchase requests"),
        ("approve", "Approve procurement"),
    ],
    "redistribution": [
        ("view", "View redistribution"),
        ("create", "Create transfer requests"),
        ("approve", "Approve transfers"),
        ("dispatch", "Dispatch transfers"),
        ("receive", "Receive transfers"),
    ],
    "forecasting": [
        ("view", "View forecasts"),
        ("run", "Run forecasting"),
    ],
    "analytics": [
        ("view", "View analytics"),
        ("export", "Export analytics"),
    ],
    "reports": [
        ("view", "View reports"),
        ("export", "Export reports"),
    ],
    "audit": [
        ("view", "View audit logs"),
        ("export", "Export audit logs"),
    ],
    "suppliers": [
        ("view", "View suppliers"),
        ("create", "Create suppliers"),
        ("update", "Update suppliers"),
    ],
    "warehouses": [
        ("view", "View warehouses"),
        ("create", "Create warehouses"),
        ("update", "Update warehouses"),
    ],
    "notifications": [
        ("view", "View notifications"),
        ("manage", "Manage notification settings"),
    ],
}


# ==========================================================
# PROCUREMENT PERMISSION CATALOG
# ==========================================================

PROCUREMENT_PERMISSIONS = [
    {
        "code": "procurement.requisition.view",
        "name": "View Purchase Requisitions",
        "module": "procurement",
        "description": "View procurement requisitions.",
    },
    {
        "code": "procurement.requisition.create",
        "name": "Create Purchase Requisitions",
        "module": "procurement",
        "description": (
            "Convert approved replenishment requests into requisitions."
        ),
    },
    {
        "code": "procurement.requisition.submit",
        "name": "Submit Purchase Requisitions",
        "module": "procurement",
        "description": "Submit purchase requisitions.",
    },
    {
        "code": "procurement.requisition.approve",
        "name": "Approve Purchase Requisitions",
        "module": "procurement",
        "description": "Approve submitted purchase requisitions.",
    },
    {
        "code": "procurement.quotation.view",
        "name": "View Supplier Quotations",
        "module": "procurement",
        "description": "View supplier quotations and comparisons.",
    },
    {
        "code": "procurement.quotation.create",
        "name": "Record Supplier Quotations",
        "module": "procurement",
        "description": "Record supplier quotation details.",
    },
    {
        "code": "procurement.quotation.select",
        "name": "Select Supplier Quotations",
        "module": "procurement",
        "description": "Select a supplier quotation for procurement.",
    },
    {
        "code": "procurement.order.view",
        "name": "View Purchase Orders",
        "module": "procurement",
        "description": "View purchase orders.",
    },
    {
        "code": "procurement.order.create",
        "name": "Create Purchase Orders",
        "module": "procurement",
        "description": (
            "Generate purchase orders from selected quotations."
        ),
    },
    {
        "code": "procurement.order.submit",
        "name": "Submit Purchase Orders",
        "module": "procurement",
        "description": "Submit purchase orders for authorization.",
    },
    {
        "code": "procurement.order.approve",
        "name": "Approve Purchase Orders",
        "module": "procurement",
        "description": "Authorize purchase orders.",
    },
    {
        "code": "procurement.order.send",
        "name": "Send Purchase Orders",
        "module": "procurement",
        "description": (
            "Dispatch approved purchase orders to suppliers."
        ),
    },
    {
        "code": "procurement.order.acknowledge",
        "name": "Acknowledge Purchase Orders",
        "module": "procurement",
        "description": (
            "Record supplier acknowledgement of purchase orders."
        ),
    },
]


# ==========================================================
# REDISTRIBUTION RECOMMENDATION PERMISSION CATALOG
# ==========================================================

REDISTRIBUTION_RECOMMENDATION_PERMISSIONS = [
    {
        "code": "redistribution.recommendation.view",
        "name": "View Redistribution Recommendations",
        "module": "redistribution",
        "description": (
            "View stock redistribution recommendations within "
            "authorized scope."
        ),
    },
    {
        "code": "redistribution.recommendation.generate",
        "name": "Generate Redistribution Recommendations",
        "module": "redistribution",
        "description": (
            "Generate demand-aware and expiry-aware redistribution "
            "recommendations."
        ),
    },
    {
        "code": "redistribution.recommendation.review",
        "name": "Review Redistribution Recommendations",
        "module": "redistribution",
        "description": (
            "Accept, reject, or defer redistribution recommendations."
        ),
    },
]


# ==========================================================
# REDISTRIBUTION OPTIMIZATION PERMISSION CATALOG
# ==========================================================

REDISTRIBUTION_OPTIMIZATION_PERMISSIONS = [
    {
        "code": "redistribution.optimization.view",
        "name": "View Redistribution Optimization",
        "module": "redistribution",
        "description": (
            "View optimized redistribution plans and results."
        ),
    },
    {
        "code": "redistribution.optimization.run",
        "name": "Run Redistribution Optimization",
        "module": "redistribution",
        "description": (
            "Run OR-Tools medicine redistribution optimization."
        ),
    },
    {
        "code": "redistribution.transport_profile.manage",
        "name": "Manage Redistribution Transport Profiles",
        "module": "redistribution",
        "description": (
            "Manage medicine-to-transport-capacity conversions."
        ),
    },
]


# ==========================================================
# REDISTRIBUTION TRANSFER PERMISSION CATALOG
# ==========================================================

REDISTRIBUTION_TRANSFER_PERMISSIONS = [
    {
        "code": "redistribution.transfer.view",
        "name": "View Transfer Requests",
        "module": "redistribution",
        "description": (
            "View authorized inter-facility transfer requests."
        ),
    },
    {
        "code": "redistribution.transfer.create",
        "name": "Create Transfer Requests",
        "module": "redistribution",
        "description": (
            "Create manual or optimization-based transfer requests."
        ),
    },
    {
        "code": "redistribution.transfer.submit",
        "name": "Submit Transfer Requests",
        "module": "redistribution",
        "description": (
            "Submit transfer requests for approval."
        ),
    },
    {
        "code": "redistribution.transfer.approve",
        "name": "Approve Transfer Requests",
        "module": "redistribution",
        "description": (
            "Approve or reject transfer requests at authorized stages."
        ),
    },
    {
        "code": "redistribution.transfer.cancel",
        "name": "Cancel Transfer Requests",
        "module": "redistribution",
        "description": (
            "Cancel transfers and release their reservations."
        ),
    },
    {
        "code": "redistribution.transfer.policy.manage",
        "name": "Manage Transfer Approval Policies",
        "module": "redistribution",
        "description": (
            "Configure transfer approval stages."
        ),
    },
]


# ==========================================================
# LOGISTICS PERMISSION CATALOG
# ==========================================================

LOGISTICS_PERMISSIONS = [
    {
        "code": "logistics.shipment.view",
        "name": "View Shipments",
        "module": "logistics",
        "description": (
            "View shipments within authorized organizational scope."
        ),
    },
    {
        "code": "logistics.shipment.create",
        "name": "Create Shipments",
        "module": "logistics",
        "description": "Create shipments for reserved transfers.",
    },
    {
        "code": "logistics.shipment.manage",
        "name": "Manage Shipments",
        "module": "logistics",
        "description": "Prepare shipments for dispatch.",
    },
    {
        "code": "logistics.shipment.dispatch",
        "name": "Dispatch Shipments",
        "module": "logistics",
        "description": "Authorize physical shipment dispatch.",
    },
    {
        "code": "logistics.shipment.track",
        "name": "Track Shipments",
        "module": "logistics",
        "description": "Record shipment tracking events and delays.",
    },
    {
        "code": "logistics.shipment.exception.manage",
        "name": "Manage Shipment Exceptions",
        "module": "logistics",
        "description": "Report and resolve shipment exceptions.",
    },
    {
        "code": "logistics.shipment.deliver",
        "name": "Report Shipment Delivery",
        "module": "logistics",
        "description": "Record shipment delivery status.",
    },
    {
        "code": "logistics.shipment.document.manage",
        "name": "Manage Shipment Documents",
        "module": "logistics",
        "description": "Upload and manage shipment documents.",
    },
    {
        "code": "logistics.transporter.view",
        "name": "View Transporters",
        "module": "logistics",
        "description": "View registered transport providers.",
    },
    {
        "code": "logistics.transporter.manage",
        "name": "Manage Transporters",
        "module": "logistics",
        "description": "Register and maintain transport providers.",
    },
    {
        "code": "logistics.vehicle.view",
        "name": "View Vehicles",
        "module": "logistics",
        "description": "View transport vehicles.",
    },
    {
        "code": "logistics.vehicle.manage",
        "name": "Manage Vehicles",
        "module": "logistics",
        "description": "Register and maintain transport vehicles.",
    },
]


# ==========================================================
# PERMISSION DESCRIPTIONS
# ==========================================================

PERMISSION_DESCRIPTIONS = {
    "inventory.view": (
        "View stock balances, batches and inventory reports."
    ),
    "inventory.receive": (
        "Receive and record incoming medicine stock."
    ),
    "inventory.issue": (
        "Issue medicine stock from inventory."
    ),
    "inventory.adjust": (
        "Adjust inventory quantities and stock balances."
    ),
    "inventory.reconcile": (
        "Approve and post physical stock reconciliation."
    ),
    "inventory.visibility.view": (
        "View eligible medicine availability across authorized facilities."
    ),
    "inventory.policy.view": (
        "View minimum, maximum and reorder stock policies."
    ),
    "inventory.policy.create": (
        "Create organization and facility stock policies."
    ),
    "inventory.policy.update": (
        "Update inactive stock policies."
    ),
    "inventory.policy.manage": (
        "Manage stock policy lifecycle, including activation "
        "and deactivation."
    ),
    "consumption.view": (
        "View facility and medicine consumption records."
    ),
    "consumption.create": (
        "Create and update draft consumption records."
    ),
    "consumption.submit": (
        "Submit monthly consumption reports."
    ),
    "consumption.approve": (
        "Review and approve submitted consumption reports."
    ),
    "replenishment.view": (
        "View replenishment requests within authorized scope."
    ),
    "replenishment.create": (
        "Create manual and policy-generated replenishment requests."
    ),
    "replenishment.submit": (
        "Submit draft requests for approval."
    ),
    "replenishment.approve": (
        "Approve or reject submitted replenishment requests."
    ),
    "replenishment.cancel": (
        "Cancel draft or submitted replenishment requests."
    ),
    "replenishment.workflow.view": (
        "View configured replenishment approval workflows."
    ),
    "replenishment.approval.view": (
        "View approval stages and decision history."
    ),
    "replenishment.workflow.manage": (
        "Create and manage approval workflows."
    ),
    "replenishment.approval.escalate": (
        "Escalate overdue replenishment approvals."
    ),
}


# ==========================================================
# STOCK POLICY PERMISSION DEFINITIONS
# ==========================================================

STOCK_POLICY_PERMISSIONS = {
    "view": "inventory.policy.view",
    "create": "inventory.policy.create",
    "update": "inventory.policy.update",
    "manage": "inventory.policy.manage",
}


# ==========================================================
# REPLENISHMENT PERMISSION DEFINITIONS
# ==========================================================

REPLENISHMENT_PERMISSIONS = {
    "view": "replenishment.view",
    "create": "replenishment.create",
    "submit": "replenishment.submit",
    "approve": "replenishment.approve",
    "cancel": "replenishment.cancel",
    "workflow_view": "replenishment.workflow.view",
    "approval_view": "replenishment.approval.view",
    "workflow_manage": "replenishment.workflow.manage",
    "approval_escalate": "replenishment.approval.escalate",
}


# ==========================================================
# PROCUREMENT PERMISSION DEFINITIONS
# ==========================================================

PROCUREMENT_PERMISSION_CODES = {
    "requisition_view": "procurement.requisition.view",
    "requisition_create": "procurement.requisition.create",
    "requisition_submit": "procurement.requisition.submit",
    "requisition_approve": "procurement.requisition.approve",
    "quotation_view": "procurement.quotation.view",
    "quotation_create": "procurement.quotation.create",
    "quotation_select": "procurement.quotation.select",
    "order_view": "procurement.order.view",
    "order_create": "procurement.order.create",
    "order_submit": "procurement.order.submit",
    "order_approve": "procurement.order.approve",
    "order_send": "procurement.order.send",
    "order_acknowledge": "procurement.order.acknowledge",
}


# ==========================================================
# REDISTRIBUTION RECOMMENDATION PERMISSION DEFINITIONS
# ==========================================================

REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES = {
    "view": "redistribution.recommendation.view",
    "generate": "redistribution.recommendation.generate",
    "review": "redistribution.recommendation.review",
}


# ==========================================================
# REDISTRIBUTION OPTIMIZATION PERMISSION DEFINITIONS
# ==========================================================

REDISTRIBUTION_OPTIMIZATION_PERMISSION_CODES = {
    "view": "redistribution.optimization.view",
    "run": "redistribution.optimization.run",
    "manage_profiles": "redistribution.transport_profile.manage",
}


# ==========================================================
# REDISTRIBUTION TRANSFER PERMISSION DEFINITIONS
# ==========================================================

REDISTRIBUTION_TRANSFER_PERMISSION_CODES = {
    "view": "redistribution.transfer.view",
    "create": "redistribution.transfer.create",
    "submit": "redistribution.transfer.submit",
    "approve": "redistribution.transfer.approve",
    "cancel": "redistribution.transfer.cancel",
    "manage_policy": "redistribution.transfer.policy.manage",
}


# ==========================================================
# LOGISTICS PERMISSION DEFINITIONS
# ==========================================================

LOGISTICS_PERMISSION_CODES = {
    "shipment_view": "logistics.shipment.view",
    "shipment_create": "logistics.shipment.create",
    "shipment_manage": "logistics.shipment.manage",
    "shipment_dispatch": "logistics.shipment.dispatch",
    "shipment_track": "logistics.shipment.track",
    "shipment_exception_manage": "logistics.shipment.exception.manage",
    "shipment_deliver": "logistics.shipment.deliver",
    "shipment_document_manage": "logistics.shipment.document.manage",
    "transporter_view": "logistics.transporter.view",
    "transporter_manage": "logistics.transporter.manage",
    "vehicle_view": "logistics.vehicle.view",
    "vehicle_manage": "logistics.vehicle.manage",
}


# ==========================================================
# ROLE ASSIGNMENT HELPER
# ==========================================================

def apply_role_assignments(assignments, assignment_name):
    """Add configured permissions to their respective roles."""

    for role_code, permission_codes in assignments.items():
        if role_code not in ROLES:
            raise ValueError(
                f"{assignment_name} role '{role_code}' "
                "does not exist in ROLES."
            )

        role_permissions = ROLES[role_code]["permissions"]

        if role_permissions == ["*"]:
            continue

        for permission_code in permission_codes:
            if permission_code not in role_permissions:
                role_permissions.append(permission_code)


# ==========================================================
# REPLENISHMENT ROLE ASSIGNMENT EXPECTATIONS
# ==========================================================

REPLENISHMENT_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.approve",
        "replenishment.cancel",
        "replenishment.workflow.view",
        "replenishment.approval.view",
        "replenishment.workflow.manage",
        "replenishment.approval.escalate",
    ],
    "REGIONAL_ADMIN": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.approve",
        "replenishment.cancel",
        "replenishment.workflow.view",
        "replenishment.approval.view",
        "replenishment.approval.escalate",
    ],
    "DISTRICT_OFFICER": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.approve",
        "replenishment.cancel",
        "replenishment.workflow.view",
        "replenishment.approval.view",
        "replenishment.approval.escalate",
    ],
    "DISTRICT_PHARMACIST": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.approve",
        "replenishment.cancel",
        "replenishment.workflow.view",
        "replenishment.approval.view",
    ],
    "FACILITY_ADMIN": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.cancel",
        "replenishment.approval.view",
    ],
    "FACILITY_PHARMACIST": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.submit",
        "replenishment.cancel",
        "replenishment.approval.view",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "replenishment.view",
        "replenishment.create",
        "replenishment.workflow.view",
        "replenishment.approval.view",
    ],
    "DATA_ANALYST": [
        "replenishment.view",
        "replenishment.workflow.view",
        "replenishment.approval.view",
    ],
    "AUDITOR": [
        "replenishment.view",
        "replenishment.workflow.view",
        "replenishment.approval.view",
    ],
}


# ==========================================================
# PROCUREMENT ROLE ASSIGNMENT EXPECTATIONS
# ==========================================================

PROCUREMENT_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "procurement.requisition.view",
        "procurement.requisition.approve",
        "procurement.quotation.view",
        "procurement.quotation.select",
        "procurement.order.view",
        "procurement.order.approve",
    ],
    "REGIONAL_ADMIN": [
        "procurement.requisition.view",
        "procurement.requisition.approve",
        "procurement.quotation.view",
        "procurement.quotation.select",
        "procurement.order.view",
        "procurement.order.approve",
    ],
    "DISTRICT_OFFICER": [
        "procurement.requisition.view",
        "procurement.requisition.create",
        "procurement.requisition.submit",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
    "DISTRICT_PHARMACIST": [
        "procurement.requisition.view",
        "procurement.requisition.create",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
    "FACILITY_ADMIN": [
        "procurement.requisition.view",
        "procurement.requisition.create",
        "procurement.requisition.submit",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
    "FACILITY_PHARMACIST": [
        "procurement.requisition.view",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "procurement.requisition.view",
        "procurement.requisition.create",
        "procurement.requisition.submit",
        "procurement.requisition.approve",
        "procurement.quotation.view",
        "procurement.quotation.create",
        "procurement.quotation.select",
        "procurement.order.view",
        "procurement.order.create",
        "procurement.order.submit",
        "procurement.order.send",
    ],
    "DATA_ANALYST": [
        "procurement.requisition.view",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
    "AUDITOR": [
        "procurement.requisition.view",
        "procurement.quotation.view",
        "procurement.order.view",
    ],
}


# ==========================================================
# REDISTRIBUTION RECOMMENDATION ROLE ASSIGNMENTS
# ==========================================================

REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.generate",
        "redistribution.recommendation.review",
    ],
    "REGIONAL_ADMIN": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.generate",
        "redistribution.recommendation.review",
    ],
    "DISTRICT_OFFICER": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.generate",
        "redistribution.recommendation.review",
    ],
    "DISTRICT_PHARMACIST": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.generate",
        "redistribution.recommendation.review",
    ],
    "FACILITY_ADMIN": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.review",
    ],
    "FACILITY_PHARMACIST": [
        "redistribution.recommendation.view",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "redistribution.recommendation.view",
        "redistribution.recommendation.generate",
        "redistribution.recommendation.review",
    ],
    "DATA_ANALYST": [
        "redistribution.recommendation.view",
    ],
    "AUDITOR": [
        "redistribution.recommendation.view",
    ],
}


# ==========================================================
# REDISTRIBUTION OPTIMIZATION ROLE ASSIGNMENTS
# ==========================================================

REDISTRIBUTION_OPTIMIZATION_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "redistribution.optimization.view",
        "redistribution.optimization.run",
        "redistribution.transport_profile.manage",
    ],
    "REGIONAL_ADMIN": [
        "redistribution.optimization.view",
        "redistribution.optimization.run",
    ],
    "DISTRICT_OFFICER": [
        "redistribution.optimization.view",
        "redistribution.optimization.run",
    ],
    "DISTRICT_PHARMACIST": [
        "redistribution.optimization.view",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "redistribution.optimization.view",
        "redistribution.optimization.run",
    ],
    "DATA_ANALYST": [
        "redistribution.optimization.view",
    ],
    "AUDITOR": [
        "redistribution.optimization.view",
    ],
    "FACILITY_PHARMACIST": [
        "redistribution.optimization.view",
    ],
}


# ==========================================================
# REDISTRIBUTION TRANSFER ROLE ASSIGNMENTS
# ==========================================================

REDISTRIBUTION_TRANSFER_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.approve",
        "redistribution.transfer.cancel",
        "redistribution.transfer.policy.manage",
    ],
    "REGIONAL_ADMIN": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.approve",
        "redistribution.transfer.cancel",
    ],
    "DISTRICT_OFFICER": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.approve",
        "redistribution.transfer.cancel",
    ],
    "DISTRICT_PHARMACIST": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.cancel",
    ],
    "FACILITY_ADMIN": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.cancel",
    ],
    "FACILITY_PHARMACIST": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.cancel",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "redistribution.transfer.view",
        "redistribution.transfer.create",
        "redistribution.transfer.submit",
        "redistribution.transfer.approve",
        "redistribution.transfer.cancel",
    ],
    "DATA_ANALYST": [
        "redistribution.transfer.view",
    ],
    "AUDITOR": [
        "redistribution.transfer.view",
    ],
}


# ==========================================================
# LOGISTICS ROLE ASSIGNMENT EXPECTATIONS
# ==========================================================

LOGISTICS_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "logistics.shipment.view",
        "logistics.shipment.create",
        "logistics.shipment.manage",
        "logistics.shipment.dispatch",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
        "logistics.shipment.document.manage",
        "logistics.transporter.view",
        "logistics.transporter.manage",
        "logistics.vehicle.view",
        "logistics.vehicle.manage",
    ],
    "REGIONAL_ADMIN": [
        "logistics.shipment.view",
        "logistics.shipment.create",
        "logistics.shipment.manage",
        "logistics.shipment.dispatch",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
        "logistics.shipment.document.manage",
        "logistics.transporter.view",
        "logistics.vehicle.view",
    ],
    "DISTRICT_OFFICER": [
        "logistics.shipment.view",
        "logistics.shipment.create",
        "logistics.shipment.manage",
        "logistics.shipment.dispatch",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
        "logistics.shipment.document.manage",
        "logistics.transporter.view",
        "logistics.vehicle.view",
    ],
    "DISTRICT_PHARMACIST": [
        "logistics.shipment.view",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
    ],
    "FACILITY_ADMIN": [
        "logistics.shipment.view",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
    ],
    "FACILITY_PHARMACIST": [
        "logistics.shipment.view",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "logistics.shipment.view",
        "logistics.shipment.create",
        "logistics.shipment.manage",
        "logistics.shipment.dispatch",
        "logistics.shipment.track",
        "logistics.shipment.exception.manage",
        "logistics.shipment.deliver",
        "logistics.shipment.document.manage",
        "logistics.transporter.view",
        "logistics.transporter.manage",
        "logistics.vehicle.view",
        "logistics.vehicle.manage",
    ],
    "DATA_ANALYST": [
        "logistics.shipment.view",
        "logistics.transporter.view",
        "logistics.vehicle.view",
    ],
    "AUDITOR": [
        "logistics.shipment.view",
        "logistics.transporter.view",
        "logistics.vehicle.view",
    ],
}


# ==========================================================
# SYSTEM ROLES AND PERMISSIONS
# ==========================================================

ROLES = {
    "SUPER_ADMIN": {
        "name": "Super Administrator",
        "description": "Full platform administration.",
        "permissions": ["*"],
    },
    "MINISTRY_ADMIN": {
        "name": "Ministry of Health Administrator",
        "description": "National-level administration.",
        "permissions": [
            "users.view",
            "users.create",
            "users.update",
            "users.assign_roles",
            "organizations.view",
            "organizations.create",
            "organizations.update",
            "facilities.view",
            "facilities.create",
            "facilities.update",
            "medicines.view",
            "medicines.create",
            "medicines.update",
            "inventory.view",
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.approve",
            "replenishment.cancel",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "replenishment.workflow.manage",
            "replenishment.approval.escalate",
            "procurement.view",
            "procurement.approve",
            "redistribution.view",
            "redistribution.approve",
            "forecasting.view",
            "analytics.view",
            "analytics.export",
            "reports.view",
            "reports.export",
            "audit.view",
            "audit.export",
        ],
    },
    "REGIONAL_ADMIN": {
        "name": "Regional Health Bureau Administrator",
        "description": "Regional administration and monitoring.",
        "permissions": [
            "users.view",
            "users.create",
            "users.update",
            "organizations.view",
            "facilities.view",
            "facilities.update",
            "medicines.view",
            "inventory.view",
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.approve",
            "replenishment.cancel",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "replenishment.approval.escalate",
            "redistribution.view",
            "redistribution.approve",
            "forecasting.view",
            "analytics.view",
            "analytics.export",
            "reports.view",
            "reports.export",
            "audit.view",
        ],
    },
    "DISTRICT_OFFICER": {
        "name": "District Health Officer",
        "description": "District-level health operations oversight.",
        "permissions": [
            "users.view",
            "facilities.view",
            "medicines.view",
            "inventory.view",
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.approve",
            "replenishment.cancel",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "replenishment.approval.escalate",
            "redistribution.view",
            "redistribution.approve",
            "forecasting.view",
            "analytics.view",
            "reports.view",
            "reports.export",
        ],
    },
    "DISTRICT_PHARMACIST": {
        "name": "District Pharmacist",
        "description": (
            "District medicine availability and pharmacy oversight."
        ),
        "permissions": [
            "facilities.view",
            "medicines.view",
            "inventory.view",
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.approve",
            "replenishment.cancel",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "redistribution.view",
            "redistribution.create",
            "redistribution.approve",
            "forecasting.view",
            "analytics.view",
            "reports.view",
        ],
    },
    "FACILITY_ADMIN": {
        "name": "Facility Administrator",
        "description": "Health facility administration.",
        "permissions": [
            "users.view",
            "users.create",
            "users.update",
            "facilities.view",
            "medicines.view",
            "inventory.view",
            "inventory.policy.view",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.cancel",
            "replenishment.approval.view",
            "redistribution.view",
            "redistribution.create",
            "reports.view",
        ],
    },
    "FACILITY_PHARMACIST": {
        "name": "Facility Pharmacist",
        "description": "Facility medicine and stock management.",
        "permissions": [
            "facilities.view",
            "medicines.view",
            "inventory.view",
            "inventory.receive",
            "inventory.issue",
            "inventory.adjust",
            "inventory.reconcile",
            "inventory.policy.view",
            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "replenishment.view",
            "replenishment.create",
            "replenishment.submit",
            "replenishment.cancel",
            "replenishment.approval.view",
            "redistribution.view",
            "redistribution.create",
            "redistribution.receive",
            "forecasting.view",
            "reports.view",
        ],
    },
    "SUPPLY_CHAIN_OFFICER": {
        "name": "Supply Chain Officer",
        "description": "Supply chain and distribution operations.",
        "permissions": [
            "medicines.view",
            "suppliers.view",
            "suppliers.create",
            "suppliers.update",
            "warehouses.view",
            "inventory.view",
            "inventory.receive",
            "inventory.issue",
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "consumption.view",
            "consumption.create",
            "replenishment.view",
            "replenishment.create",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "procurement.view",
            "procurement.create",
            "redistribution.view",
            "redistribution.create",
            "redistribution.approve",
            "redistribution.dispatch",
            "redistribution.receive",
            "reports.view",
        ],
    },
    "DATA_ANALYST": {
        "name": "Data Analyst",
        "description": "Analytics, forecasting and reporting.",
        "permissions": [
            "medicines.view",
            "facilities.view",
            "inventory.view",
            "inventory.policy.view",
            "replenishment.view",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "consumption.view",
            "forecasting.view",
            "forecasting.run",
            "analytics.view",
            "analytics.export",
            "reports.view",
            "reports.export",
        ],
    },
    "AUDITOR": {
        "name": "Auditor",
        "description": "Read-only audit and compliance access.",
        "permissions": [
            "users.view",
            "organizations.view",
            "facilities.view",
            "medicines.view",
            "inventory.view",
            "inventory.policy.view",
            "consumption.view",
            "replenishment.view",
            "replenishment.workflow.view",
            "replenishment.approval.view",
            "procurement.view",
            "redistribution.view",
            "analytics.view",
            "reports.view",
            "reports.export",
            "audit.view",
            "audit.export",
        ],
    },
}


# ==========================================================
# APPLY ROLE ASSIGNMENTS
# ==========================================================

apply_role_assignments(
    REPLENISHMENT_ROLE_ASSIGNMENTS,
    "Replenishment",
)

apply_role_assignments(
    PROCUREMENT_ROLE_ASSIGNMENTS,
    "Procurement",
)

apply_role_assignments(
    REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS,
    "Redistribution recommendation",
)

apply_role_assignments(
    REDISTRIBUTION_OPTIMIZATION_ROLE_ASSIGNMENTS,
    "Redistribution optimization",
)

apply_role_assignments(
    REDISTRIBUTION_TRANSFER_ROLE_ASSIGNMENTS,
    "Redistribution transfer",
)

apply_role_assignments(
    LOGISTICS_ROLE_ASSIGNMENTS,
    "Logistics",
)


# ==========================================================
# ROLES THAT MUST HAVE INVENTORY VIEW
# ==========================================================

INVENTORY_VIEW_ROLES = [
    "SUPER_ADMIN",
    "MINISTRY_ADMIN",
    "REGIONAL_ADMIN",
    "DISTRICT_OFFICER",
    "DISTRICT_PHARMACIST",
    "FACILITY_ADMIN",
    "FACILITY_PHARMACIST",
    "SUPPLY_CHAIN_OFFICER",
    "DATA_ANALYST",
    "AUDITOR",
]


# ==========================================================
# INTER-FACILITY STOCK VISIBILITY PERMISSIONS
# ==========================================================

INVENTORY_VISIBILITY_PERMISSION = "inventory.visibility.view"

INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS = {
    role: [INVENTORY_VISIBILITY_PERMISSION]
    for role in [
        "MINISTRY_ADMIN",
        "REGIONAL_ADMIN",
        "DISTRICT_OFFICER",
        "DISTRICT_PHARMACIST",
        "FACILITY_ADMIN",
        "FACILITY_PHARMACIST",
        "SUPPLY_CHAIN_OFFICER",
        "DATA_ANALYST",
        "AUDITOR",
    ]
}


# ==========================================================
# APPLY INVENTORY VISIBILITY ROLE ASSIGNMENTS
# ==========================================================

apply_role_assignments(
    INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS,
    "Inventory visibility",
)


# ==========================================================
# STOCK POLICY ROLE ASSIGNMENT EXPECTATIONS
# ==========================================================

STOCK_POLICY_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        "inventory.policy.view",
        "inventory.policy.create",
        "inventory.policy.update",
        "inventory.policy.manage",
    ],
    "REGIONAL_ADMIN": [
        "inventory.policy.view",
        "inventory.policy.create",
        "inventory.policy.update",
        "inventory.policy.manage",
    ],
    "DISTRICT_OFFICER": [
        "inventory.policy.view",
        "inventory.policy.create",
        "inventory.policy.update",
        "inventory.policy.manage",
    ],
    "DISTRICT_PHARMACIST": [
        "inventory.policy.view",
        "inventory.policy.create",
        "inventory.policy.update",
        "inventory.policy.manage",
    ],
    "FACILITY_ADMIN": [
        "inventory.policy.view",
    ],
    "FACILITY_PHARMACIST": [
        "inventory.policy.view",
    ],
    "SUPPLY_CHAIN_OFFICER": [
        "inventory.policy.view",
        "inventory.policy.create",
        "inventory.policy.update",
    ],
    "DATA_ANALYST": [
        "inventory.policy.view",
    ],
    "AUDITOR": [
        "inventory.policy.view",
    ],
}


# ==========================================================
# MANAGEMENT COMMAND
# ==========================================================

class Command(BaseCommand):
    help = "Create default MediResilience AI roles and permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        permission_map = {}

        # --------------------------------------------------
        # 1. CREATE OR UPDATE GENERAL PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE("Seeding permission catalog...")
        )

        for module, actions in PERMISSIONS.items():
            for action, name in actions:
                code = f"{module}.{action}"

                defaults = {
                    "name": name,
                    "module": module,
                    "is_active": True,
                }

                description = PERMISSION_DESCRIPTIONS.get(code)

                if description is not None:
                    defaults["description"] = description

                permission, created = (
                    AccessPermission.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                )

                permission_map[code] = permission

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created permission: {code}"
                        )
                    )
                else:
                    self.stdout.write(f"Updated permission: {code}")

        # --------------------------------------------------
        # 2. CREATE OR UPDATE SPECIALIZED PERMISSIONS
        # --------------------------------------------------

        specialized_catalogs = [
            (
                "procurement",
                PROCUREMENT_PERMISSIONS,
            ),
            (
                "redistribution recommendation",
                REDISTRIBUTION_RECOMMENDATION_PERMISSIONS,
            ),
            (
                "redistribution optimization",
                REDISTRIBUTION_OPTIMIZATION_PERMISSIONS,
            ),
            (
                "redistribution transfer",
                REDISTRIBUTION_TRANSFER_PERMISSIONS,
            ),
            (
                "logistics",
                LOGISTICS_PERMISSIONS,
            ),
        ]

        for catalog_name, catalog in specialized_catalogs:
            self.stdout.write(
                self.style.NOTICE(
                    f"Seeding {catalog_name} permissions..."
                )
            )

            for definition in catalog:
                code = definition["code"]

                defaults = {
                    "name": definition["name"],
                    "module": definition["module"],
                    "description": definition["description"],
                    "is_active": True,
                }

                permission, created = (
                    AccessPermission.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                )

                permission_map[code] = permission

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created permission: {code}"
                        )
                    )
                else:
                    self.stdout.write(f"Updated permission: {code}")

        # --------------------------------------------------
        # 3. VALIDATE REQUIRED PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE("Validating required permissions...")
        )

        required_permission_sets = {
            "inventory.view": ["inventory.view"],
            "inventory visibility": [
                INVENTORY_VISIBILITY_PERMISSION,
            ],
            "stock policy": list(STOCK_POLICY_PERMISSIONS.values()),
            "replenishment": list(REPLENISHMENT_PERMISSIONS.values()),
            "procurement": list(PROCUREMENT_PERMISSION_CODES.values()),
            "redistribution recommendation": list(
                REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
            ),
            "redistribution optimization": list(
                REDISTRIBUTION_OPTIMIZATION_PERMISSION_CODES.values()
            ),
            "redistribution transfer": list(
                REDISTRIBUTION_TRANSFER_PERMISSION_CODES.values()
            ),
            "logistics": list(LOGISTICS_PERMISSION_CODES.values()),
        }

        for catalog_name, permission_codes in (
            required_permission_sets.items()
        ):
            for permission_code in permission_codes:
                permission = permission_map.get(permission_code)

                if permission is None:
                    raise ValueError(
                        f"Required {catalog_name} permission "
                        f"'{permission_code}' is missing."
                    )

                if not permission.is_active:
                    raise ValueError(
                        f"Permission '{permission_code}' must be active."
                    )

        inventory_view = permission_map["inventory.view"]

        visibility_permission = permission_map[
            INVENTORY_VISIBILITY_PERMISSION
        ]

        # --------------------------------------------------
        # 4. VALIDATE ROLE PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE("Validating system role permissions...")
        )

        for role_code, definition in ROLES.items():
            if definition["permissions"] == ["*"]:
                continue

            for permission_code in definition["permissions"]:
                if permission_code not in permission_map:
                    raise ValueError(
                        f"Unknown permission '{permission_code}' "
                        f"assigned to role '{role_code}'."
                    )

        # --------------------------------------------------
        # 5. VALIDATE ROLE ASSIGNMENT POLICIES
        # --------------------------------------------------

        assignment_policies = [
            (
                "Inventory visibility",
                INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS,
                {INVENTORY_VISIBILITY_PERMISSION},
            ),
            (
                "Stock policy",
                STOCK_POLICY_ROLE_ASSIGNMENTS,
                set(STOCK_POLICY_PERMISSIONS.values()),
            ),
            (
                "Replenishment",
                REPLENISHMENT_ROLE_ASSIGNMENTS,
                set(REPLENISHMENT_PERMISSIONS.values()),
            ),
            (
                "Procurement",
                PROCUREMENT_ROLE_ASSIGNMENTS,
                set(PROCUREMENT_PERMISSION_CODES.values()),
            ),
            (
                "Redistribution recommendation",
                REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution optimization",
                REDISTRIBUTION_OPTIMIZATION_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_OPTIMIZATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution transfer",
                REDISTRIBUTION_TRANSFER_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_TRANSFER_PERMISSION_CODES.values()
                ),
            ),
            (
                "Logistics",
                LOGISTICS_ROLE_ASSIGNMENTS,
                set(LOGISTICS_PERMISSION_CODES.values()),
            ),
        ]

        for policy_name, assignments, permission_set in assignment_policies:
            self.stdout.write(
                self.style.NOTICE(
                    f"Validating {policy_name.lower()} role assignments..."
                )
            )

            for role_code, expected_permissions in assignments.items():
                if role_code not in ROLES:
                    raise ValueError(
                        f"{policy_name} role '{role_code}' "
                        "does not exist in ROLES."
                    )

                actual_permissions = set(
                    ROLES[role_code]["permissions"]
                )

                expected_permissions = set(expected_permissions)

                actual_policy_permissions = (
                    actual_permissions & permission_set
                )

                if actual_policy_permissions != expected_permissions:
                    raise ValueError(
                        f"{policy_name} permissions for role "
                        f"'{role_code}' do not match the configured "
                        "role assignment policy. "
                        f"Expected: {sorted(expected_permissions)}. "
                        f"Found: {sorted(actual_policy_permissions)}."
                    )

        # --------------------------------------------------
        # 6. VALIDATE INVENTORY VIEW ROLE CONFIGURATION
        # --------------------------------------------------

        for role_code in INVENTORY_VIEW_ROLES:
            if role_code not in ROLES:
                raise ValueError(
                    f"Inventory view role '{role_code}' "
                    "does not exist in ROLES."
                )

            role_permissions = ROLES[role_code]["permissions"]

            if (
                role_permissions != ["*"]
                and "inventory.view" not in role_permissions
            ):
                raise ValueError(
                    f"Role '{role_code}' must include inventory.view."
                )

        # --------------------------------------------------
        # 7. CREATE OR UPDATE ROLES
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE("Seeding system roles...")
        )

        for code, definition in ROLES.items():
            role, created = Role.objects.update_or_create(
                code=code,
                defaults={
                    "name": definition["name"],
                    "description": definition["description"],
                    "is_system_role": True,
                    "is_active": True,
                },
            )

            if definition["permissions"] == ["*"]:
                permissions = list(permission_map.values())
            else:
                permissions = [
                    permission_map[permission_code]
                    for permission_code in definition["permissions"]
                ]

            role.permissions.set(permissions)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created role: {code}")
                )
            else:
                self.stdout.write(f"Updated role: {code}")

        # --------------------------------------------------
        # 8. VERIFY INVENTORY VIEW PERMISSION
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying inventory.view role assignments..."
            )
        )

        for role_code in INVENTORY_VIEW_ROLES:
            role = Role.objects.get(code=role_code)

            if not role.permissions.filter(pk=inventory_view.pk).exists():
                raise ValueError(
                    f"Role '{role_code}' is missing inventory.view."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: inventory.view verified."
                )
            )

        # --------------------------------------------------
        # 9. VERIFY ALL ROLE ASSIGNMENT POLICIES
        # --------------------------------------------------

        verification_policies = [
            (
                "Inventory visibility",
                INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS,
                {INVENTORY_VISIBILITY_PERMISSION},
            ),
            (
                "Stock policy",
                STOCK_POLICY_ROLE_ASSIGNMENTS,
                set(STOCK_POLICY_PERMISSIONS.values()),
            ),
            (
                "Replenishment",
                REPLENISHMENT_ROLE_ASSIGNMENTS,
                set(REPLENISHMENT_PERMISSIONS.values()),
            ),
            (
                "Procurement",
                PROCUREMENT_ROLE_ASSIGNMENTS,
                set(PROCUREMENT_PERMISSION_CODES.values()),
            ),
            (
                "Redistribution recommendation",
                REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution optimization",
                REDISTRIBUTION_OPTIMIZATION_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_OPTIMIZATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution transfer",
                REDISTRIBUTION_TRANSFER_ROLE_ASSIGNMENTS,
                set(
                    REDISTRIBUTION_TRANSFER_PERMISSION_CODES.values()
                ),
            ),
            (
                "Logistics",
                LOGISTICS_ROLE_ASSIGNMENTS,
                set(LOGISTICS_PERMISSION_CODES.values()),
            ),
        ]

        for policy_name, assignments, permission_set in (
            verification_policies
        ):
            self.stdout.write(
                self.style.NOTICE(
                    f"Verifying {policy_name.lower()} role assignments..."
                )
            )

            for role_code, expected_permissions in assignments.items():
                role = Role.objects.get(code=role_code)

                assigned_codes = set(
                    role.permissions.filter(
                        code__in=permission_set
                    ).values_list(
                        "code",
                        flat=True,
                    )
                )

                expected_codes = set(expected_permissions)

                if assigned_codes != expected_codes:
                    raise ValueError(
                        f"{policy_name} permission verification failed "
                        f"for role '{role_code}'. "
                        f"Expected: {sorted(expected_codes)}. "
                        f"Found: {sorted(assigned_codes)}."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{role_code}: {policy_name.lower()} "
                        "permissions verified."
                    )
                )

        # --------------------------------------------------
        # 10. VERIFY SUPER ADMIN PERMISSIONS
        # --------------------------------------------------

        super_admin_role = Role.objects.get(code="SUPER_ADMIN")

        super_admin_permission_sets = [
            (
                "Inventory visibility",
                {INVENTORY_VISIBILITY_PERMISSION},
            ),
            (
                "Redistribution recommendation",
                set(
                    REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution optimization",
                set(
                    REDISTRIBUTION_OPTIMIZATION_PERMISSION_CODES.values()
                ),
            ),
            (
                "Redistribution transfer",
                set(
                    REDISTRIBUTION_TRANSFER_PERMISSION_CODES.values()
                ),
            ),
            (
                "Logistics",
                set(LOGISTICS_PERMISSION_CODES.values()),
            ),
        ]

        for policy_name, expected_codes in super_admin_permission_sets:
            assigned_codes = set(
                super_admin_role.permissions.filter(
                    code__in=expected_codes
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            if assigned_codes != expected_codes:
                raise ValueError(
                    f"SUPER_ADMIN is missing one or more "
                    f"{policy_name.lower()} permissions. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"SUPER_ADMIN: all {policy_name.lower()} "
                    "permissions verified."
                )
            )

        # --------------------------------------------------
        # 11. VERIFY PERMISSION METADATA
        # --------------------------------------------------

        metadata_catalogs = [
            ("Procurement", PROCUREMENT_PERMISSIONS),
            (
                "Redistribution recommendation",
                REDISTRIBUTION_RECOMMENDATION_PERMISSIONS,
            ),
            (
                "Redistribution optimization",
                REDISTRIBUTION_OPTIMIZATION_PERMISSIONS,
            ),
            (
                "Redistribution transfer",
                REDISTRIBUTION_TRANSFER_PERMISSIONS,
            ),
            ("Logistics", LOGISTICS_PERMISSIONS),
        ]

        for catalog_name, catalog in metadata_catalogs:
            self.stdout.write(
                self.style.NOTICE(
                    f"Verifying {catalog_name.lower()} permission metadata..."
                )
            )

            for definition in catalog:
                permission = permission_map[definition["code"]]
                permission.refresh_from_db()

                if (
                    permission.code != definition["code"]
                    or permission.name != definition["name"]
                    or permission.module != definition["module"]
                    or permission.description != definition["description"]
                    or not permission.is_active
                ):
                    raise ValueError(
                        f"{catalog_name} permission metadata "
                        f"verification failed for '{definition['code']}'."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{permission.code} | "
                        f"{permission.name} | "
                        f"Module: {permission.module} | "
                        f"Active: {permission.is_active}"
                    )
                )

        # --------------------------------------------------
        # 12. VERIFY INVENTORY PERMISSION METADATA
        # --------------------------------------------------

        inventory_view.refresh_from_db()

        self.stdout.write(
            self.style.NOTICE(
                "Verified inventory.view permission metadata:"
            )
        )

        self.stdout.write(f"Code: {inventory_view.code}")
        self.stdout.write(f"Name: {inventory_view.name}")
        self.stdout.write(f"Module: {inventory_view.module}")
        self.stdout.write(
            f"Description: {inventory_view.description}"
        )
        self.stdout.write(f"Active: {inventory_view.is_active}")

        # --------------------------------------------------
        # 13. VERIFY INVENTORY VISIBILITY METADATA
        # --------------------------------------------------

        visibility_permission.refresh_from_db()

        if (
            visibility_permission.code != INVENTORY_VISIBILITY_PERMISSION
            or visibility_permission.module != "inventory"
            or not visibility_permission.is_active
        ):
            raise ValueError(
                "Inventory visibility permission metadata "
                "verification failed."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Inventory visibility permission metadata verified."
            )
        )

        # --------------------------------------------------
        # 14. VERIFY SUPPLY CHAIN OFFICER PROCUREMENT COUNT
        # --------------------------------------------------

        supply_chain_role = Role.objects.get(
            code="SUPPLY_CHAIN_OFFICER"
        )

        procurement_permission_set = set(
            PROCUREMENT_PERMISSION_CODES.values()
        )

        supply_chain_procurement_codes = set(
            supply_chain_role.permissions.filter(
                code__in=procurement_permission_set
            ).values_list(
                "code",
                flat=True,
            )
        )

        expected_supply_chain_codes = set(
            PROCUREMENT_ROLE_ASSIGNMENTS["SUPPLY_CHAIN_OFFICER"]
        )

        if supply_chain_procurement_codes != expected_supply_chain_codes:
            raise ValueError(
                "Supply Chain Officer procurement permission "
                "verification failed. "
                f"Expected: {sorted(expected_supply_chain_codes)}. "
                f"Found: {sorted(supply_chain_procurement_codes)}."
            )

        if len(supply_chain_procurement_codes) != 11:
            raise ValueError(
                "Supply Chain Officer must have exactly 11 "
                "granular procurement permissions. "
                f"Found: {len(supply_chain_procurement_codes)}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "SUPPLY_CHAIN_OFFICER: exactly 11 granular "
                "procurement permissions verified."
            )
        )

        # --------------------------------------------------
        # 15. VERIFY REDISTRIBUTION TRANSFER PERMISSIONS
        # --------------------------------------------------

        transfer_permission_set = set(
            REDISTRIBUTION_TRANSFER_PERMISSION_CODES.values()
        )

        self.stdout.write(
            self.style.NOTICE(
                "Verifying redistribution transfer permissions..."
            )
        )

        for role_code, expected_permissions in (
            REDISTRIBUTION_TRANSFER_ROLE_ASSIGNMENTS.items()
        ):
            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=transfer_permission_set
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    "Redistribution transfer permission verification "
                    f"failed for '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: {len(expected_codes)} transfer "
                    "permissions verified."
                )
            )

        if len(transfer_permission_set) != 6:
            raise ValueError(
                "Redistribution transfer must contain exactly "
                f"6 permissions. Found: {len(transfer_permission_set)}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "All six redistribution transfer permissions verified."
            )
        )

        # --------------------------------------------------
        # 16. VERIFY LOGISTICS PERMISSIONS
        # --------------------------------------------------

        logistics_permission_set = set(
            LOGISTICS_PERMISSION_CODES.values()
        )

        self.stdout.write(
            self.style.NOTICE(
                "Verifying logistics permissions and role assignments..."
            )
        )

        for role_code, expected_permissions in (
            LOGISTICS_ROLE_ASSIGNMENTS.items()
        ):
            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=logistics_permission_set
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    "Logistics permission verification failed "
                    f"for '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: {len(expected_codes)} logistics "
                    "permissions verified."
                )
            )

        if len(logistics_permission_set) != 12:
            raise ValueError(
                "The logistics catalog must contain exactly 12 "
                f"permissions. Found: {len(logistics_permission_set)}."
            )

        super_admin_logistics_codes = set(
            super_admin_role.permissions.filter(
                code__in=logistics_permission_set
            ).values_list(
                "code",
                flat=True,
            )
        )

        if super_admin_logistics_codes != logistics_permission_set:
            raise ValueError(
                "SUPER_ADMIN is missing one or more logistics permissions."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "All 12 logistics permissions verified, including "
                "SUPER_ADMIN access."
            )
        )

        # --------------------------------------------------
        # 17. SUCCESS MESSAGES
        # --------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "RBAC roles and permissions seeded successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "All 10 system roles have inventory.view."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "All configured roles have inventory.visibility.view."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Stock policy permissions and role assignments "
                "verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Replenishment request and workflow permissions "
                "and role assignments verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Procurement permissions and role assignments "
                "verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Supply Chain Officer has exactly 11 "
                "granular procurement permissions."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Redistribution recommendation permissions and "
                "role assignments verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Redistribution optimization permissions and "
                "role assignments verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Redistribution transfer permissions and "
                "role assignments verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Logistics permissions and role assignments "
                "verified successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "All RBAC permission metadata and role assignments "
                "verified successfully."
            )
        )
