import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("mediresilience.api")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Log the actual unhandled exception and its traceback.
        logger.error(
            "Unhandled API exception: %s",
            str(exc),
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        return Response(
            {
                "success": False,
                "message": "An unexpected server error occurred.",
                "errors": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "success": False,
            "message": "The request could not be processed.",
            "errors": response.data,
        },
        status=response.status_code,
        headers=response.headers,
    )
