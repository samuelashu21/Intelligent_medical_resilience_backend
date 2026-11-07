import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.organizations.models import Organization


class FacilityType(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.name


class Facility(models.Model):
    """
    Healthcare facility belonging to an administrative organization.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=200,
    )

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    facility_type = models.ForeignKey(
        FacilityType,
        on_delete=models.PROTECT,
        related_name="facilities",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="facilities",
    )

    address = models.TextField(
        blank=True,
    )

    contact_person = models.CharField(
        max_length=150,
        blank=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    contact_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["facility_type"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.organization_id and not self.organization.is_active:
            raise ValidationError(
                {"organization": "The organization must be active."}
            )

        if self.facility_type_id and not self.facility_type.is_active:
            raise ValidationError(
                {"facility_type": "The facility type must be active."}
            )

        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValidationError(
                {"latitude": "Latitude must be between -90 and 90."}
            )

        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValidationError(
                {"longitude": "Longitude must be between -180 and 180."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})" 