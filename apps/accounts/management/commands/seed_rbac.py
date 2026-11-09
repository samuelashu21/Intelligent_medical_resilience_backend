from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import (
    Role,
    AccessPermission,
    RolePermission,
)


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
        ("view", "View inventory"),
        ("receive", "Receive stock"),
        ("issue", "Issue stock"),
        ("adjust", "Adjust stock"),
        ("reconcile", "Reconcile Inventory"),
    ],

    "consumption": [
        ("view", "View Medicine Consumption"),
        ("create", "Record Medicine Consumption"),
        ("submit", "Submit Consumption Reports"),
        ("approve", "Approve Consumption Reports"),
    ],

    "replenishment": [
        ("view", "View replenishment requests"),
        ("create", "Create replenishment requests"),
        ("approve", "Approve replenishment requests"),
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
# PERMISSION DESCRIPTIONS
# ==========================================================

PERMISSION_DESCRIPTIONS = {
    "inventory.reconcile": (
        "Approve and post physical stock reconciliation."
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
}


# ==========================================================
# SYSTEM ROLES AND PERMISSIONS
# ==========================================================

ROLES = {
    # ------------------------------------------------------
    # SUPER ADMIN
    # ------------------------------------------------------

    "SUPER_ADMIN": {
        "name": "Super Administrator",
        "description": "Full platform administration.",
        "permissions": ["*"],
    },

    # ------------------------------------------------------
    # MINISTRY ADMIN
    # ------------------------------------------------------

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

            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",

            "replenishment.view",
            "replenishment.approve",

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

    # ------------------------------------------------------
    # REGIONAL ADMIN
    # ------------------------------------------------------

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

            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",

            "replenishment.view",
            "replenishment.approve",

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

    # ------------------------------------------------------
    # DISTRICT OFFICER
    # ------------------------------------------------------

    "DISTRICT_OFFICER": {
        "name": "District Health Officer",
        "description": "District-level health operations oversight.",
        "permissions": [
            "users.view",
            "facilities.view",
            "medicines.view",
            "inventory.view",

            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",

            "replenishment.view",
            "replenishment.approve",

            "redistribution.view",
            "redistribution.approve",

            "forecasting.view",

            "analytics.view",

            "reports.view",
            "reports.export",
        ],
    },

    # ------------------------------------------------------
    # DISTRICT PHARMACIST
    # ------------------------------------------------------

    "DISTRICT_PHARMACIST": {
        "name": "District Pharmacist",
        "description": (
            "District medicine availability and pharmacy oversight."
        ),
        "permissions": [
            "facilities.view",
            "medicines.view",
            "inventory.view",

            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",

            "replenishment.view",
            "replenishment.approve",

            "redistribution.view",
            "redistribution.create",
            "redistribution.approve",

            "forecasting.view",

            "analytics.view",

            "reports.view",
        ],
    },

    # ------------------------------------------------------
    # FACILITY ADMIN
    # ------------------------------------------------------

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

            "consumption.view",
            "consumption.create",
            "consumption.submit",
            "consumption.approve",

            "replenishment.view",
            "replenishment.create",

            "redistribution.view",
            "redistribution.create",

            "reports.view",
        ],
    },

    # ------------------------------------------------------
    # FACILITY PHARMACIST
    # ------------------------------------------------------

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

            "consumption.view",
            "consumption.create",
            "consumption.submit",

            "replenishment.view",
            "replenishment.create",

            "redistribution.view",
            "redistribution.create",
            "redistribution.receive",

            "forecasting.view",

            "reports.view",
        ],
    },

    # ------------------------------------------------------
    # SUPPLY CHAIN OFFICER
    # ------------------------------------------------------

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

            "consumption.view",
            "consumption.create",

            "replenishment.view",

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

    # ------------------------------------------------------
    # DATA ANALYST
    # ------------------------------------------------------

    "DATA_ANALYST": {
        "name": "Data Analyst",
        "description": "Analytics, forecasting and reporting.",
        "permissions": [
            "medicines.view",
            "facilities.view",
            "inventory.view",

            "consumption.view",

            "forecasting.view",
            "forecasting.run",

            "analytics.view",
            "analytics.export",

            "reports.view",
            "reports.export",
        ],
    },

    # ------------------------------------------------------
    # AUDITOR
    # ------------------------------------------------------

    "AUDITOR": {
        "name": "Auditor",
        "description": "Read-only audit and compliance access.",
        "permissions": [
            "users.view",
            "organizations.view",
            "facilities.view",
            "medicines.view",
            "inventory.view",

            "consumption.view",

            "replenishment.view",
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
# MANAGEMENT COMMAND
# ==========================================================

class Command(BaseCommand):

    help = "Create default MediResilience AI roles and permissions."

    @transaction.atomic
    def handle(self, *args, **options):

        permission_map = {}

        # --------------------------------------------------
        # 1. CREATE OR UPDATE PERMISSIONS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Seeding permission catalog..."
            )
        )

        for module, actions in PERMISSIONS.items():

            for action, name in actions:

                code = f"{module}.{action}"

                defaults = {
                    "name": name,
                    "module": module,
                    "is_active": True,
                }

                if code in PERMISSION_DESCRIPTIONS:
                    defaults["description"] = (
                        PERMISSION_DESCRIPTIONS[code]
                    )

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
        # 2. CREATE OR UPDATE ROLES
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Seeding system roles..."
            )
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

                permissions = list(
                    permission_map.values()
                )

            else:

                permissions = []

                for permission_code in definition["permissions"]:

                    permission = permission_map.get(
                        permission_code
                    )

                    if permission is None:
                        raise ValueError(
                            f"Unknown permission '{permission_code}' "
                            f"assigned to role '{code}'."
                        )

                    permissions.append(permission)

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
        # 3. SUCCESS MESSAGE
        # --------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "RBAC roles and permissions seeded successfully."
            )
        )