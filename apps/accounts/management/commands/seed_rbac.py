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
    # Existing general procurement permissions (preserved).
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
    # Exactly 11 granular permissions.
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

            # Existing general procurement permissions preserved.
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
# APPLY PROCUREMENT ROLE ASSIGNMENTS
# ==========================================================

for role_code, procurement_permissions in (
    PROCUREMENT_ROLE_ASSIGNMENTS.items()
):
    if role_code not in ROLES:
        raise ValueError(
            f"Procurement role '{role_code}' does not exist in ROLES."
        )

    role_permissions = ROLES[role_code]["permissions"]

    if role_permissions != ["*"]:
        for permission_code in procurement_permissions:
            if permission_code not in role_permissions:
                role_permissions.append(permission_code)


# ==========================================================
# APPLY REDISTRIBUTION RECOMMENDATION ROLE ASSIGNMENTS
# ==========================================================

for role_code, recommendation_permissions in (
    REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS.items()
):
    if role_code not in ROLES:
        raise ValueError(
            "Redistribution recommendation role "
            f"'{role_code}' does not exist in ROLES."
        )

    role_permissions = ROLES[role_code]["permissions"]

    if role_permissions != ["*"]:
        for permission_code in recommendation_permissions:
            if permission_code not in role_permissions:
                role_permissions.append(permission_code)


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
# INTER-FACILITY STOCK VISIBILITY PERMISSION
# ==========================================================

INVENTORY_VISIBILITY_PERMISSION = "inventory.visibility.view"


# ==========================================================
# INTER-FACILITY STOCK VISIBILITY ROLE ASSIGNMENTS
# ==========================================================

INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS = {
    "MINISTRY_ADMIN": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "REGIONAL_ADMIN": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "DISTRICT_OFFICER": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "DISTRICT_PHARMACIST": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "FACILITY_ADMIN": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "FACILITY_PHARMACIST": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "SUPPLY_CHAIN_OFFICER": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "DATA_ANALYST": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
    "AUDITOR": [
        INVENTORY_VISIBILITY_PERMISSION,
    ],
}


# ==========================================================
# APPLY INTER-FACILITY STOCK VISIBILITY ROLE ASSIGNMENTS
# ==========================================================

for role_code, visibility_permissions in (
    INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS.items()
):
    if role_code not in ROLES:
        raise ValueError(
            f"Inventory visibility role '{role_code}' "
            "does not exist in ROLES."
        )

    role_permissions = ROLES[role_code]["permissions"]

    if role_permissions != ["*"]:
        for permission_code in visibility_permissions:
            if permission_code not in role_permissions:
                role_permissions.append(permission_code)


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

    help = (
        "Create default MediResilience AI roles and permissions."
    )

    @transaction.atomic
    def handle(self, *args, **options):

        permission_map = {}

        # --------------------------------------------------
        # 1. CREATE OR UPDATE EXISTING PERMISSIONS
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
                    self.stdout.write(
                        f"Updated permission: {code}"
                    )

        # --------------------------------------------------
        # 2. CREATE OR UPDATE PROCUREMENT PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE("Seeding procurement permissions...")
        )

        for definition in PROCUREMENT_PERMISSIONS:

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
                self.stdout.write(
                    f"Updated permission: {code}"
                )

        # --------------------------------------------------
        # 2A. CREATE OR UPDATE REDISTRIBUTION RECOMMENDATION
        #     PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Seeding redistribution recommendation permissions..."
            )
        )

        for definition in REDISTRIBUTION_RECOMMENDATION_PERMISSIONS:

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
                self.stdout.write(
                    f"Updated permission: {code}"
                )

        # --------------------------------------------------
        # 3. VALIDATE REQUIRED INVENTORY PERMISSION
        # --------------------------------------------------

        inventory_view = permission_map.get("inventory.view")

        if inventory_view is None:
            raise ValueError(
                "Required permission inventory.view "
                "is missing from the permission catalog."
            )

        # --------------------------------------------------
        # 3A. VALIDATE INTER-FACILITY VISIBILITY PERMISSION
        # --------------------------------------------------

        visibility_permission = permission_map.get(
            INVENTORY_VISIBILITY_PERMISSION
        )

        if visibility_permission is None:
            raise ValueError(
                "Required permission "
                "'inventory.visibility.view' is missing "
                "from the permission catalog."
            )

        if not visibility_permission.is_active:
            raise ValueError(
                "Permission 'inventory.visibility.view' "
                "must be active."
            )

        # --------------------------------------------------
        # 3B. VALIDATE REDISTRIBUTION RECOMMENDATION
        #     PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating redistribution recommendation permissions..."
            )
        )

        for permission_code in (
            REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
        ):
            permission = permission_map.get(permission_code)

            if permission is None:
                raise ValueError(
                    "Required redistribution recommendation permission "
                    f"'{permission_code}' is missing."
                )

            if not permission.is_active:
                raise ValueError(
                    f"Permission '{permission_code}' must be active."
                )

        # --------------------------------------------------
        # 4. VALIDATE STOCK POLICY PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating stock policy permissions..."
            )
        )

        for permission_name, permission_code in (
            STOCK_POLICY_PERMISSIONS.items()
        ):
            if permission_code not in permission_map:
                raise ValueError(
                    "Required stock policy permission "
                    f"'{permission_code}' is missing."
                )

        # --------------------------------------------------
        # 5. VALIDATE REPLENISHMENT PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating replenishment permissions..."
            )
        )

        for permission_name, permission_code in (
            REPLENISHMENT_PERMISSIONS.items()
        ):
            if permission_code not in permission_map:
                raise ValueError(
                    "Required replenishment permission "
                    f"'{permission_code}' is missing."
                )

        # --------------------------------------------------
        # 6. VALIDATE PROCUREMENT PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating procurement permissions..."
            )
        )

        for permission_code in PROCUREMENT_PERMISSION_CODES.values():

            if permission_code not in permission_map:
                raise ValueError(
                    "Required procurement permission "
                    f"'{permission_code}' is missing."
                )

        # --------------------------------------------------
        # 6A. VALIDATE INVENTORY VISIBILITY ROLE ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating inter-facility stock visibility assignments..."
            )
        )

        for role_code, expected_permissions in (
            INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS.items()
        ):

            if role_code not in ROLES:
                raise ValueError(
                    f"Inventory visibility role '{role_code}' "
                    "does not exist in ROLES."
                )

            actual_permissions = set(
                ROLES[role_code]["permissions"]
            )

            expected_permissions = set(expected_permissions)

            for permission_code in expected_permissions:
                if permission_code not in actual_permissions:
                    raise ValueError(
                        f"Role '{role_code}' must include "
                        f"'{permission_code}'."
                    )

            actual_visibility_permissions = (
                actual_permissions
                & {INVENTORY_VISIBILITY_PERMISSION}
            )

            if actual_visibility_permissions != expected_permissions:
                raise ValueError(
                    f"Inventory visibility permissions for role "
                    f"'{role_code}' do not match the configured "
                    f"role assignment policy. "
                    f"Expected: {sorted(expected_permissions)}. "
                    f"Found: {sorted(actual_visibility_permissions)}."
                )

        # --------------------------------------------------
        # 6B. VALIDATE REDISTRIBUTION RECOMMENDATION
        #     ROLE ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating redistribution recommendation role assignments..."
            )
        )

        recommendation_permission_set = set(
            REDISTRIBUTION_RECOMMENDATION_PERMISSION_CODES.values()
        )

        for role_code, expected_permissions in (
            REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS.items()
        ):

            if role_code not in ROLES:
                raise ValueError(
                    "Redistribution recommendation role "
                    f"'{role_code}' does not exist in ROLES."
                )

            actual_permissions = set(
                ROLES[role_code]["permissions"]
            )

            expected_permissions = set(expected_permissions)

            actual_recommendation_permissions = (
                actual_permissions
                & recommendation_permission_set
            )

            if actual_recommendation_permissions != expected_permissions:
                raise ValueError(
                    "Redistribution recommendation permissions for "
                    f"role '{role_code}' do not match the configured "
                    f"role assignment policy. "
                    f"Expected: {sorted(expected_permissions)}. "
                    f"Found: {sorted(actual_recommendation_permissions)}."
                )

        # --------------------------------------------------
        # 7. VALIDATE ALL ROLE PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating system role permissions..."
            )
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
        # 8. VALIDATE INVENTORY VIEW ROLE CONFIGURATION
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
                    f"Role '{role_code}' must include "
                    "inventory.view."
                )

        # --------------------------------------------------
        # 9. VALIDATE STOCK POLICY ROLE CONFIGURATION
        # --------------------------------------------------

        for role_code, expected_permissions in (
            STOCK_POLICY_ROLE_ASSIGNMENTS.items()
        ):

            if role_code not in ROLES:
                raise ValueError(
                    f"Stock policy role '{role_code}' "
                    "does not exist in ROLES."
                )

            actual_permissions = set(
                ROLES[role_code]["permissions"]
            )

            expected_permissions = set(expected_permissions)

            for permission_code in expected_permissions:

                if permission_code not in actual_permissions:
                    raise ValueError(
                        f"Role '{role_code}' must include "
                        f"'{permission_code}'."
                    )

            actual_policy_permissions = (
                actual_permissions
                & set(STOCK_POLICY_PERMISSIONS.values())
            )

            if actual_policy_permissions != expected_permissions:
                raise ValueError(
                    f"Stock policy permissions for role "
                    f"'{role_code}' do not match the configured "
                    f"role assignment policy. "
                    f"Expected: {sorted(expected_permissions)}. "
                    f"Found: {sorted(actual_policy_permissions)}."
                )

        # --------------------------------------------------
        # 10. VALIDATE REPLENISHMENT ROLE CONFIGURATION
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating replenishment role assignments..."
            )
        )

        for role_code, expected_permissions in (
            REPLENISHMENT_ROLE_ASSIGNMENTS.items()
        ):

            if role_code not in ROLES:
                raise ValueError(
                    f"Replenishment role '{role_code}' "
                    "does not exist in ROLES."
                )

            actual_permissions = set(
                ROLES[role_code]["permissions"]
            )

            expected_permissions = set(expected_permissions)

            actual_replenishment_permissions = (
                actual_permissions
                & set(REPLENISHMENT_PERMISSIONS.values())
            )

            if actual_replenishment_permissions != expected_permissions:
                raise ValueError(
                    f"Replenishment permissions for role "
                    f"'{role_code}' do not match the configured "
                    f"role assignment policy. "
                    f"Expected: {sorted(expected_permissions)}. "
                    f"Found: {sorted(actual_replenishment_permissions)}."
                )

        # --------------------------------------------------
        # 11. VALIDATE PROCUREMENT ROLE CONFIGURATION
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Validating procurement role assignments..."
            )
        )

        procurement_permission_set = set(
            PROCUREMENT_PERMISSION_CODES.values()
        )

        for role_code, expected_permissions in (
            PROCUREMENT_ROLE_ASSIGNMENTS.items()
        ):

            if role_code not in ROLES:
                raise ValueError(
                    f"Procurement role '{role_code}' "
                    "does not exist in ROLES."
                )

            actual_permissions = set(
                ROLES[role_code]["permissions"]
            )

            expected_permissions = set(expected_permissions)

            actual_procurement_permissions = (
                actual_permissions
                & procurement_permission_set
            )

            if actual_procurement_permissions != expected_permissions:
                raise ValueError(
                    f"Procurement permissions for role "
                    f"'{role_code}' do not match the configured "
                    f"role assignment policy. "
                    f"Expected: {sorted(expected_permissions)}. "
                    f"Found: {sorted(actual_procurement_permissions)}."
                )

        # --------------------------------------------------
        # 12. CREATE OR UPDATE ROLES
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

            # SUPER_ADMIN receives every catalog permission.
            if definition["permissions"] == ["*"]:

                permissions = list(permission_map.values())

            else:

                permissions = [
                    permission_map[permission_code]
                    for permission_code in definition["permissions"]
                ]

            # Synchronize role permissions.
            role.permissions.set(permissions)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created role: {code}"
                    )
                )
            else:
                self.stdout.write(
                    f"Updated role: {code}"
                )

        # --------------------------------------------------
        # 13. VERIFY INVENTORY VIEW PERMISSION
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying inventory.view role assignments..."
            )
        )

        for role_code in INVENTORY_VIEW_ROLES:

            role = Role.objects.get(code=role_code)

            has_permission = role.permissions.filter(
                pk=inventory_view.pk
            ).exists()

            if not has_permission:
                raise ValueError(
                    f"Role '{role_code}' is missing "
                    "inventory.view."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: inventory.view verified."
                )
            )

        # --------------------------------------------------
        # 13A. VERIFY INTER-FACILITY STOCK VISIBILITY ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying inter-facility stock visibility assignments..."
            )
        )

        for role_code, expected_permissions in (
            INVENTORY_VISIBILITY_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code=INVENTORY_VISIBILITY_PERMISSION
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    f"Inventory visibility permission verification "
                    f"failed for role '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: inter-facility stock visibility verified."
                )
            )

        # --------------------------------------------------
        # 13B. VERIFY SUPER ADMIN VISIBILITY PERMISSION
        # --------------------------------------------------

        super_admin_role = Role.objects.get(
            code="SUPER_ADMIN"
        )

        if not super_admin_role.permissions.filter(
            code=INVENTORY_VISIBILITY_PERMISSION
        ).exists():
            raise ValueError(
                "SUPER_ADMIN is missing inventory.visibility.view."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "SUPER_ADMIN: inter-facility stock visibility verified."
            )
        )

        # --------------------------------------------------
        # 13C. VERIFY REDISTRIBUTION RECOMMENDATION ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying redistribution recommendation role assignments..."
            )
        )

        for role_code, expected_permissions in (
            REDISTRIBUTION_RECOMMENDATION_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=recommendation_permission_set
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    "Redistribution recommendation permission "
                    f"verification failed for role '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: redistribution recommendation "
                    "permissions verified."
                )
            )

        # --------------------------------------------------
        # 13D. VERIFY SUPER ADMIN RECOMMENDATION PERMISSIONS
        # --------------------------------------------------

        super_admin_recommendation_codes = set(
            super_admin_role.permissions.filter(
                code__in=recommendation_permission_set
            ).values_list(
                "code",
                flat=True,
            )
        )

        if (
            super_admin_recommendation_codes
            != recommendation_permission_set
        ):
            raise ValueError(
                "SUPER_ADMIN is missing one or more redistribution "
                "recommendation permissions. "
                f"Expected: {sorted(recommendation_permission_set)}. "
                f"Found: {sorted(super_admin_recommendation_codes)}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "SUPER_ADMIN: all redistribution recommendation "
                "permissions verified."
            )
        )

        # --------------------------------------------------
        # 14. VERIFY STOCK POLICY PERMISSION ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying stock policy role assignments..."
            )
        )

        for role_code, expected_permissions in (
            STOCK_POLICY_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=STOCK_POLICY_PERMISSIONS.values()
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    f"Stock policy permission verification failed "
                    f"for role '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: stock policy permissions verified."
                )
            )

        # --------------------------------------------------
        # 15. VERIFY STOCK POLICY PERMISSION METADATA
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying stock policy permission metadata..."
            )
        )

        for permission_code in STOCK_POLICY_PERMISSIONS.values():

            permission = permission_map[permission_code]
            permission.refresh_from_db()

            self.stdout.write(
                self.style.SUCCESS(
                    f"{permission.code} | "
                    f"{permission.name} | "
                    f"Module: {permission.module} | "
                    f"Active: {permission.is_active}"
                )
            )

        # --------------------------------------------------
        # 16. VERIFY REPLENISHMENT ROLE PERMISSION ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying replenishment role assignments..."
            )
        )

        for role_code, expected_permissions in (
            REPLENISHMENT_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=REPLENISHMENT_PERMISSIONS.values()
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    f"Replenishment permission verification failed "
                    f"for role '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: replenishment permissions verified."
                )
            )

        # --------------------------------------------------
        # 17. VERIFY REPLENISHMENT PERMISSION METADATA
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying replenishment permission metadata..."
            )
        )

        for permission_code in REPLENISHMENT_PERMISSIONS.values():

            permission = permission_map[permission_code]
            permission.refresh_from_db()

            self.stdout.write(
                self.style.SUCCESS(
                    f"{permission.code} | "
                    f"{permission.name} | "
                    f"Module: {permission.module} | "
                    f"Active: {permission.is_active}"
                )
            )

        # --------------------------------------------------
        # 18. VERIFY PROCUREMENT ROLE ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying procurement role assignments..."
            )
        )

        for role_code, expected_permissions in (
            PROCUREMENT_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(code=role_code)

            assigned_codes = set(
                role.permissions.filter(
                    code__in=procurement_permission_set
                ).values_list(
                    "code",
                    flat=True,
                )
            )

            expected_codes = set(expected_permissions)

            if assigned_codes != expected_codes:
                raise ValueError(
                    f"Procurement permission verification failed "
                    f"for role '{role_code}'. "
                    f"Expected: {sorted(expected_codes)}. "
                    f"Found: {sorted(assigned_codes)}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{role_code}: procurement permissions verified."
                )
            )

        # --------------------------------------------------
        # 19. VERIFY PROCUREMENT PERMISSION METADATA
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying procurement permission metadata..."
            )
        )

        for definition in PROCUREMENT_PERMISSIONS:

            permission = permission_map[definition["code"]]
            permission.refresh_from_db()

            if (
                permission.name != definition["name"]
                or permission.module != "procurement"
                or permission.description != definition["description"]
                or not permission.is_active
            ):
                raise ValueError(
                    "Procurement permission metadata verification "
                    f"failed for '{definition['code']}'."
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
        # 19A. VERIFY REDISTRIBUTION RECOMMENDATION METADATA
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying redistribution recommendation permission metadata..."
            )
        )

        for definition in REDISTRIBUTION_RECOMMENDATION_PERMISSIONS:

            permission = permission_map[definition["code"]]
            permission.refresh_from_db()

            if (
                permission.code != definition["code"]
                or permission.name != definition["name"]
                or permission.module != "redistribution"
                or permission.description != definition["description"]
                or not permission.is_active
            ):
                raise ValueError(
                    "Redistribution recommendation permission metadata "
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
        # 20. VERIFY INVENTORY VIEW PERMISSION METADATA
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
        self.stdout.write(f"Description: {inventory_view.description}")
        self.stdout.write(f"Active: {inventory_view.is_active}")

        # --------------------------------------------------
        # 20A. VERIFY INTER-FACILITY VISIBILITY PERMISSION METADATA
        # --------------------------------------------------

        visibility_permission.refresh_from_db()

        if (
            visibility_permission.code != INVENTORY_VISIBILITY_PERMISSION
            or visibility_permission.module != "inventory"
            or not visibility_permission.is_active
        ):
            raise ValueError(
                "Inventory visibility permission metadata verification "
                "failed."
            )

        self.stdout.write(
            self.style.NOTICE(
                "Verified inventory.visibility.view permission metadata:"
            )
        )

        self.stdout.write(f"Code: {visibility_permission.code}")
        self.stdout.write(f"Name: {visibility_permission.name}")
        self.stdout.write(f"Module: {visibility_permission.module}")
        self.stdout.write(
            f"Description: {visibility_permission.description}"
        )
        self.stdout.write(f"Active: {visibility_permission.is_active}")

        # --------------------------------------------------
        # 21. VERIFY SUPPLY CHAIN OFFICER HAS EXACTLY 11
        #     GRANULAR PROCUREMENT PERMISSIONS
        # --------------------------------------------------

        supply_chain_role = Role.objects.get(
            code="SUPPLY_CHAIN_OFFICER"
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

        if (
            supply_chain_procurement_codes
            != expected_supply_chain_codes
        ):
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
        # 22. SUCCESS MESSAGE
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
                "All 10 system roles have inventory.visibility.view."
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