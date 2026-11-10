from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from django.conf import settings


class StandardResultsPagination(PageNumberPagination):

    page_size = settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)

    page_size_query_param = "page_size"

    max_page_size = settings.API_MAX_PAGE_SIZE

    def get_paginated_response(self, data):

        return Response(
            {
                "success": True,
                "pagination": {
                    "count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "current_page": self.page.number,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "results": data,
            }
        )
