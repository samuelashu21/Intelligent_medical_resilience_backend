 
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import (
    Role,
    AccessPermission,
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
        ("view", "View Inventory"),
        ("receive", "Receive stock"),
        ("issue", "Issue stock"),
        ("adjust", "Adjust stock"),
        ("reconcile", "Reconcile Inventory"),

        # Stock policy permissions
        ("policy.view", "View Stock Policies"),
        ("policy.create", "Create Stock Policies"),
        ("policy.update", "Update Stock Policies"),
        ("policy.manage", "Activate and Deactivate Stock Policies"),
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

    # Stock policy descriptions
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

            # Stock policy permissions
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",

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

            # Stock policy permissions
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",

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

            # Stock policy permissions
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",

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

            # Stock policy permissions
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            "inventory.policy.manage",

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

            # Stock policy permissions
            # Create, update and manage are policy-based.
            "inventory.policy.view",

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

            # Stock policy permissions
            # Read-only access.
            "inventory.policy.view",

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

            # Stock policy permissions
            "inventory.policy.view",
            "inventory.policy.create",
            "inventory.policy.update",
            # Manage is policy-based and is not granted globally.

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

            # Stock policy permissions
            # Read-only access.
            "inventory.policy.view",

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

            # Stock policy permissions
            # Read-only access.
            "inventory.policy.view",

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
        # 2. VALIDATE REQUIRED INVENTORY PERMISSION
        # --------------------------------------------------

        inventory_view = permission_map.get(
            "inventory.view"
        )

        if inventory_view is None:
            raise ValueError(
                "Required permission inventory.view "
                "is missing from the permission catalog."
            )

        # --------------------------------------------------
        # 3. VALIDATE STOCK POLICY PERMISSIONS
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
                    f"Required stock policy permission "
                    f"'{permission_code}' is missing."
                )

        # --------------------------------------------------
        # 4. VALIDATE ALL ROLE PERMISSIONS
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
        # 5. VALIDATE INVENTORY VIEW ROLE CONFIGURATION
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
        # 6. VALIDATE STOCK POLICY ROLE CONFIGURATION
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

            # Ensure no additional stock policy permissions
            # are accidentally granted beyond the matrix.
            actual_policy_permissions = (
                actual_permissions
                & set(STOCK_POLICY_PERMISSIONS.values())
            )

            if actual_policy_permissions != expected_permissions:
                raise ValueError(
                    f"Stock policy permissions for role "
                    f"'{role_code}' do not match the configured "
                    f"role assignment policy."
                )

        # --------------------------------------------------
        # 7. CREATE OR UPDATE ROLES
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
        # 8. VERIFY INVENTORY VIEW PERMISSION
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying inventory.view role assignments..."
            )
        )

        for role_code in INVENTORY_VIEW_ROLES:

            role = Role.objects.get(
                code=role_code
            )

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
        # 9. VERIFY STOCK POLICY PERMISSION ASSIGNMENTS
        # --------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                "Verifying stock policy role assignments..."
            )
        )

        for role_code, expected_permissions in (
            STOCK_POLICY_ROLE_ASSIGNMENTS.items()
        ):

            role = Role.objects.get(
                code=role_code
            )

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
        # 10. VERIFY STOCK POLICY PERMISSION METADATA
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
        # 11. VERIFY INVENTORY VIEW PERMISSION METADATA
        # --------------------------------------------------

        inventory_view.refresh_from_db()

        self.stdout.write(
            self.style.NOTICE(
                "Verified inventory.view permission metadata:"
            )
        )

        self.stdout.write(
            f"Code: {inventory_view.code}"
        )

        self.stdout.write(
            f"Name: {inventory_view.name}"
        )

        self.stdout.write(
            f"Module: {inventory_view.module}"
        )

        self.stdout.write(
            f"Description: {inventory_view.description}"
        )

        self.stdout.write(
            f"Active: {inventory_view.is_active}"
        )

        # --------------------------------------------------
        # 12. SUCCESS MESSAGE
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
                "Stock policy permissions and role assignments "
                "verified successfully."
            )
        )
 