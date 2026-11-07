from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)


class OrganizationModelTests(TestCase):

    def setUp(self):
        self.national_type = OrganizationUnitType.objects.create(
            code="NATIONAL_TEST",
            name="National",
            level=1,
        )

        self.region_type = OrganizationUnitType.objects.create(
            code="REGION_TEST",
            name="Region",
            level=2,
            parent_type=self.national_type,
        )

        self.district_type = OrganizationUnitType.objects.create(
            code="DISTRICT_TEST",
            name="District",
            level=3,
            parent_type=self.region_type,
        )

        self.national = Organization.objects.create(
            name="Test National Authority",
            code="TEST-NATIONAL",
            organization_type=self.national_type,
        )

        self.region = Organization.objects.create(
            name="Test Region",
            code="TEST-REGION",
            organization_type=self.region_type,
            parent=self.national,
        )

        self.district = Organization.objects.create(
            name="Test District",
            code="TEST-DISTRICT",
            organization_type=self.district_type,
            parent=self.region,
        )

    def test_organization_hierarchy(self):
        self.assertEqual(
            self.region.parent,
            self.national,
        )

        self.assertEqual(
            self.district.parent,
            self.region,
        )

    def test_get_ancestors(self):
        ancestors = self.district.get_ancestors()

        self.assertEqual(
            [item.id for item in ancestors],
            [self.region.id, self.national.id],
        )

    def test_get_descendants(self):
        descendants = self.national.get_descendants()

        descendant_ids = {
            item.id for item in descendants
        }

        self.assertIn(self.region.id, descendant_ids)
        self.assertIn(self.district.id, descendant_ids)

    def test_cannot_create_organization_without_required_parent(self):
        with self.assertRaises(ValidationError):
            Organization.objects.create(
                name="Orphan District",
                code="ORPHAN-DISTRICT",
                organization_type=self.district_type,
            )

    def test_cannot_use_wrong_parent_type(self):
        with self.assertRaises(ValidationError):
            Organization.objects.create(
                name="Invalid District",
                code="INVALID-DISTRICT",
                organization_type=self.district_type,
                parent=self.national,
            )

    def test_cannot_create_circular_relationship(self):
        self.region.parent = self.district

        with self.assertRaises(ValidationError):
            self.region.save()