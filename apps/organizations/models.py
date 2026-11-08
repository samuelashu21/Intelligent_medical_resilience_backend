# import uuid
 
# from django.core.exceptions import ValidationError
# from django.db import models


# class OrganizationUnitType(models.Model):
#     """
#     Configurable organization hierarchy types.

#     Examples:
#     NATIONAL, REGION, ZONE, DISTRICT.
#     """

#     id = models.UUIDField(
#         primary_key=True,
#         default=uuid.uuid4,
#         editable=False,
#     )

#     code = models.CharField(
#         max_length=50,
#         unique=True,
#     )

#     name = models.CharField(
#         max_length=150,
#     )

#     description = models.TextField(
#         blank=True,
#     )

#     level = models.PositiveIntegerField(
#         help_text="Hierarchy level. Smaller values represent higher levels.",
#     )

#     parent_type = models.ForeignKey(
#         "self",
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name="child_types",
#     )

#     is_active = models.BooleanField(
#         default=True,
#     )

#     created_at = models.DateTimeField(
#         auto_now_add=True,
#     )

#     updated_at = models.DateTimeField(
#         auto_now=True,
#     )

#     class Meta:
#         ordering = ["level", "name"]
#         verbose_name = "Organization Unit Type"
#         verbose_name_plural = "Organization Unit Types"

#     def clean(self):
#         if self.parent_type_id:
#             if self.parent_type_id == self.pk:
#                 raise ValidationError(
#                     {"parent_type": "An organization type cannot be its own parent."}
#                 )

#             if self.parent_type.level >= self.level:
#                 raise ValidationError(
#                     {"level": "A child organization type must have a greater level than its parent type."}
#                 )

#     def __str__(self):
#         return f"{self.name} ({self.code})"


# class Organization(models.Model):
#     """
#     Represents an administrative organization.

#     Organizations can form a configurable parent-child hierarchy.
#     """

#     id = models.UUIDField(
#         primary_key=True,
#         default=uuid.uuid4,
#         editable=False,
#     )

#     name = models.CharField(
#         max_length=200,
#     )

#     code = models.CharField(
#         max_length=100,
#         unique=True,
#     )

#     organization_type = models.ForeignKey(
#         OrganizationUnitType,
#         on_delete=models.PROTECT,
#         related_name="organizations",
#     )

#     parent = models.ForeignKey(
#         "self",
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name="children",
#     )

#     description = models.TextField(
#         blank=True,
#     )

#     address = models.TextField(
#         blank=True,
#     )

#     contact_email = models.EmailField(
#         blank=True,
#     )

#     contact_phone = models.CharField(
#         max_length=30,
#         blank=True,
#     )

#     is_active = models.BooleanField(
#         default=True,
#     )

#     created_at = models.DateTimeField(
#         auto_now_add=True,
#     )

#     updated_at = models.DateTimeField(
#         auto_now=True,
#     )

#     class Meta:
#         ordering = ["name"]
#         indexes = [
#             models.Index(fields=["code"]),
#             models.Index(fields=["parent"]),
#             models.Index(fields=["organization_type"]),
#             models.Index(fields=["is_active"]),
#         ]

#     def clean(self):
#         if self.parent_id:
#             if self.parent_id == self.pk:
#                 raise ValidationError(
#                     {"parent": "An organization cannot be its own parent."}
#                 )

#             if self.parent.organization_type.level >= self.organization_type.level:
#                 raise ValidationError(
#                     {
#                         "parent": (
#                             "The parent organization must have a higher "
#                             "hierarchy level than this organization."
#                         )
#                     }
#                 )

#             if not self.parent.is_active:
#                 raise ValidationError(
#                     {"parent": "Cannot assign an inactive parent organization."}
#                 )

#             # Prevent circular organization relationships.
#             ancestor = self.parent

#             while ancestor is not None:
#                 if ancestor.pk == self.pk:
#                     raise ValidationError(
#                         {"parent": "Circular organization relationships are not allowed."}
#                     )

#                 ancestor = ancestor.parent

#         elif self.organization_type.parent_type_id:
#             raise ValidationError(
#                 {
#                     "parent": (
#                         "An organization of this type must have a parent "
#                         "organization."
#                     )
#                 }
#             )

#         if self.parent_id:
#             if (
#                 self.organization_type.parent_type_id
#                 and self.parent.organization_type_id
#                 != self.organization_type.parent_type_id
#             ):
#                 raise ValidationError(
#                     {
#                         "organization_type": (
#                             "The parent organization has an incompatible type."
#                         )
#                     }
#                 )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)

#     def get_ancestors(self):
#         ancestors = []
#         current = self.parent

#         while current:
#             ancestors.append(current)
#             current = current.parent

#         return ancestors

#     def get_descendants(self):
#         descendants = []
#         pending = list(self.children.all())

#         while pending:
#             current = pending.pop(0)
#             descendants.append(current)
#             pending.extend(current.children.all())
 
#         return descendants

#     def __str__(self):
#         return f"{self.name} ({self.code})"






import uuid

from django.core.exceptions import ValidationError
from django.db import models


class OrganizationUnitType(models.Model):
    """
    Configurable organization hierarchy types.

    Examples:
    NATIONAL, REGION, ZONE, DISTRICT.
    """

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

    level = models.PositiveIntegerField(
        help_text="Hierarchy level. Smaller values represent higher levels.",
    )

    parent_type = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="child_types",
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
        ordering = ["level", "name"]
        verbose_name = "Organization Unit Type"
        verbose_name_plural = "Organization Unit Types"

    def clean(self):
        if self.parent_type_id:
            if self.parent_type_id == self.pk:
                raise ValidationError(
                    {"parent_type": "An organization type cannot be its own parent."}
                )

            if self.parent_type.level >= self.level:
                raise ValidationError(
                    {"level": "A child organization type must have a greater level than its parent type."}
                )

    def __str__(self):
        return f"{self.name} ({self.code})"


class Organization(models.Model):
    """
    Represents an administrative organization.

    Organizations can form a configurable parent-child hierarchy.
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

    organization_type = models.ForeignKey(
        OrganizationUnitType,
        on_delete=models.PROTECT,
        related_name="organizations",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    description = models.TextField(
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    contact_phone = models.CharField(
        max_length=30,
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
            models.Index(fields=["parent"]),
            models.Index(fields=["organization_type"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError(
                    {"parent": "An organization cannot be its own parent."}
                )

            if self.parent.organization_type.level >= self.organization_type.level:
                raise ValidationError(
                    {
                        "parent": (
                            "The parent organization must have a higher "
                            "hierarchy level than this organization."
                        )
                    }
                )

            if not self.parent.is_active:
                raise ValidationError(
                    {"parent": "Cannot assign an inactive parent organization."}
                )

            # Prevent circular organization relationships.
            ancestor = self.parent

            while ancestor is not None:
                if ancestor.pk == self.pk:
                    raise ValidationError(
                        {"parent": "Circular organization relationships are not allowed."}
                    )

                ancestor = ancestor.parent

        elif getattr(self, "organization_type_id", None) and self.organization_type.parent_type_id:
            raise ValidationError(
                {
                    "parent": (
                        "An organization of this type must have a parent "
                        "organization."
                    )
                }
            )

        if self.parent_id:
            if (
                getattr(self, "organization_type_id", None)
                and self.organization_type.parent_type_id
                and self.parent.organization_type_id
                != self.organization_type.parent_type_id
            ):
                raise ValidationError(
                    {
                        "organization_type": (
                            "The parent organization has an incompatible type."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_ancestors(self):
        ancestors = []
        current = self.parent

        while current:
            ancestors.append(current)
            current = current.parent

        return ancestors

    def get_descendants(self):
        descendants = []
        pending = list(self.children.all())

        while pending:
            current = pending.pop(0)
            descendants.append(current)
            pending.extend(current.children.all())

        return descendants

    def __str__(self):
        return f"{self.name} ({self.code})"