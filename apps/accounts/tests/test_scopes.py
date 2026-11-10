from django.test import TestCase

from apps.accounts.models import (
    User,
    Role,
    AccessPermission,
)

from apps.accounts.services import assign_role, user_has_permission

from apps.accounts.scope_services import (
    user_can_access_organization,
    user_can_access_facility,
    get_user_accessible_facility_ids,
)

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.facilities.models import (
    Facility,
    FacilityType,
)


class OrganizationScopeTests(TestCase):

    def setUp(self):
        # Organization hierarchy
        self.region_type = OrganizationUnitType.objects.create(
            code="SCOPE_REGION",
            name="Scope Region",
            level=1,
        )

        self.district_type = OrganizationUnitType.objects.create(
            code="SCOPE_DISTRICT",
            name="Scope District",
            level=2,
            parent_type=self.region_type,
        )

        self.region = Organization.objects.create(
            name="Region A",
            code="SCOPE-REGION-A",
            organization_type=self.region_type,
        )

        self.district_a = Organization.objects.create(
            name="District A",
            code="SCOPE-DISTRICT-A",
            organization_type=self.district_type,
            parent=self.region,
        )

        self.district_b = Organization.objects.create(
            name="District B",
            code="SCOPE-DISTRICT-B",
            organization_type=self.district_type,
            parent=self.region,
        )

        # Facility types
        self.hospital_type = FacilityType.objects.create(
            code="SCOPE_HOSPITAL",
            name="Hospital",
        )

        self.facility_a = Facility.objects.create(
            name="Hospital A",
            code="SCOPE-FACILITY-A",
            organization=self.district_a,
            facility_type=self.hospital_type,
        )

        self.facility_b = Facility.objects.create(
            name="Hospital B",
            code="SCOPE-FACILITY-B",
            organization=self.district_b,
            facility_type=self.hospital_type,
        )

        # User
        self.user = User.objects.create_user(
            email="district@example.com",
            username="district_user",
            password="SecurePassword123!",
        )

        # Role and permission
        self.role = Role.objects.create(
            code="SCOPE_TEST_ROLE",
            name="Scope Test Role",
        )

        self.inventory_permission = AccessPermission.objects.create(
            code="inventory.view",
            name="View Inventory",
            module="inventory",
        )

        self.role.permissions.add(self.inventory_permission)

    def test_district_assignment_can_access_descendant_facility(self):
        assign_role(
            user=self.user,
            role=self.role,
            organization=self.district_a,
        )

        self.assertTrue(
            user_can_access_facility(
                self.user,
                self.facility_a,
            )
        )

        self.assertFalse(
            user_can_access_facility(
                self.user,
                self.facility_b,
            )
        )

    def test_region_assignment_can_access_both_districts(self):
        assign_role(
            user=self.user,
            role=self.role,
            organization=self.region,
        )

        self.assertTrue(
            user_can_access_organization(
                self.user,
                self.district_a,
            )
        )

        self.assertTrue(
            user_can_access_organization(
                self.user,
                self.district_b,
            )
        )

        self.assertTrue(
            user_can_access_facility(
                self.user,
                self.facility_a,
            )
        )

        self.assertTrue(
            user_can_access_facility(
                self.user,
                self.facility_b,
            )
        )

    def test_facility_assignment_is_restricted(self):
        assign_role(
            user=self.user,
            role=self.role,
            facility=self.facility_a,
        )

        self.assertTrue(
            user_can_access_facility(
                self.user,
                self.facility_a,
            )
        )

        self.assertFalse(
            user_can_access_facility(
                self.user,
                self.facility_b,
            )
        )

        self.assertFalse(
            user_can_access_organization(
                self.user,
                self.district_a,
            )
        )

    def test_permission_is_checked_with_matching_scope(self):
        assign_role(
            user=self.user,
            role=self.role,
            facility=self.facility_a,
        )

        self.assertTrue(
            user_has_permission(
                self.user,
                "inventory.view",
                facility=self.facility_a,
            )
        )

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
                facility=self.facility_b,
            )
        )

    def test_role_permission_cannot_be_combined_with_another_role_scope(self):
        # Role A: permission, but only Facility A.
        assign_role(
            user=self.user,
            role=self.role,
            facility=self.facility_a,
        )

        # Role B: scope to District B, but no inventory permission.
        other_role = Role.objects.create(
            code="SCOPE_WITHOUT_PERMISSION",
            name="Scope Without Permission",
        )

        assign_role(
            user=self.user,
            role=other_role,
            organization=self.district_b,
        )

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
                facility=self.facility_b,
            )
        )

    def test_accessible_facility_ids(self):
        assign_role(
            user=self.user,
            role=self.role,
            organization=self.district_a,
        )

        accessible = get_user_accessible_facility_ids(self.user)

        self.assertIn(self.facility_a.id, accessible)
        self.assertNotIn(self.facility_b.id, accessible)
