import requests

from django.conf import settings


class RedistributionServiceError(Exception):
    pass


def optimize_redistribution(payload):

    base_url = settings.ML_SERVICE_URL.rstrip("/")

    url = (
        f"{base_url}/api/v1/redistribution/optimize"
    )

    headers = {
        "X-ML-Service-Key": settings.ML_SERVICE_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=90,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        raise RedistributionServiceError(
            "Unable to generate redistribution recommendations."
        ) from exc