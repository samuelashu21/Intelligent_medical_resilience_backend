import requests

from django.conf import settings


class RiskServiceError(Exception):
    pass


def prioritize_supply_chain_risks(observations):

    base_url = settings.ML_SERVICE_URL.rstrip("/")

    url = f"{base_url}/api/v1/risk/prioritize"

    headers = {
        "X-ML-Service-Key": settings.ML_SERVICE_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "observations": observations,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        raise RiskServiceError(
            "Unable to obtain supply-chain risk prioritization."
        ) from exc