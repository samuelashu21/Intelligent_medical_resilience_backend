# backend/apps/logistics/document_validators.py

from django.core.exceptions import ValidationError


ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def validate_shipment_document(uploaded_file):

    filename = uploaded_file.name.lower()

    if not any(
        filename.endswith(ext)
        for ext in ALLOWED_DOCUMENT_EXTENSIONS
    ):
        raise ValidationError(
            "Only PDF, JPG, JPEG and PNG documents are allowed."
        )

    if uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(
            "Document size cannot exceed 10 MB."
        )