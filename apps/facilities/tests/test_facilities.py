from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.facilities.models import (
    Facility,
    FacilityType,
)


class FacilityModelTests(TestCase):

    def setUp(self):
        organization_type = OrganizationUnitType.objects.create(
            code="FACILITY_TEST_ORG",
            name="Test Organization",
            level=1,
        )

        self.organization = Organization.objects.create(
            name="Test District",
            code="FACILITY-TEST-DISTRICT",
            organization_type=organization_type,
        )

        self.facility_type = FacilityType.objects.create(
            code="TEST_HOSPITAL",
            name="Test Hospital",
        )

    def test_create_facility(self):
        facility = Facility.objects.create(
            name="Test General Hospital",
            code="TEST-HOSPITAL-001",
            facility_type=self.facility_type,
            organization=self.organization,
        )

        self.assertEqual(
            facility.organization,
            self.organization,
        )

    def test_facility_coordinates(self):
        facility = Facility.objects.create(
            name="Test Health Center",
            code="TEST-HC-001",
            facility_type=self.facility_type,
            organization=self.organization,
            latitude="11.5936000",
            longitude="37.3908000",
        )

        self.assertEqual(str(facility.latitude), "11.5936000")

    def test_invalid_latitude(self):
        with self.assertRaises(ValidationError):
            Facility.objects.create(
                name="Invalid Facility",
                code="INVALID-FACILITY",
                facility_type=self.facility_type,
                organization=self.organization,
                latitude="120.0000000",
            )
