
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "success": False,
                "message": "An unexpected server error occurred.",
                "errors": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    error_data = response.data

    return Response(
        {
            "success": False,
            "message": "The request could not be processed.",
            "errors": error_data,
        },
        status=response.status_code,
        headers=response.headers,
    )
