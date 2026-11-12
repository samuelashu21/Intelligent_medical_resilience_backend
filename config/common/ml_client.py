import requests

from django.conf import settings


class MLServiceError(Exception):
    pass


class MLServiceClient:

    def __init__(self):

        self.base_url = settings.ML_SERVICE_URL.rstrip("/")

        self.api_key = settings.ML_SERVICE_API_KEY

        self.timeout = getattr(
            settings,
            "ML_SERVICE_TIMEOUT",
            30,
        )

    def _headers(self):

        return {
            "X-ML-Service-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, endpoint, payload):

        url = (
            f"{self.base_url}"
            f"/api/v1/{endpoint.lstrip('/')}"
        )

        try:

            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )

            response.raise_for_status()

            return response.json()

        except requests.Timeout as exc:

            raise MLServiceError(
                "The ML service request timed out."
            ) from exc

        except requests.ConnectionError as exc:

            raise MLServiceError(
                "The ML service is currently unavailable."
            ) from exc

        except requests.HTTPError as exc:

            raise MLServiceError(
                f"ML service returned HTTP {response.status_code}."
            ) from exc

        except requests.RequestException as exc:

            raise MLServiceError(
                "ML service request failed."
            ) from exc

    def forecast(self, payload):

        return self._post(
            "forecasting/predict",
            payload,
        )

    def predict_stockout(self, payload):

        return self._post(
            "stockout/predict",
            payload,
        )

    def detect_anomalies(self, payload):

        return self._post(
            "anomaly/detect",
            payload,
        )


ml_client = MLServiceClient()