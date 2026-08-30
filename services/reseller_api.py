# services/reseller_api.py

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import (
    RESELLER_API_URL,
    RESELLER_API_KEY,
)

logger = logging.getLogger(__name__)


class ResellerAPIError(Exception):
    """Raised when the reseller API returns an error."""


class ResellerAPI:
    """
    Client for the reseller REST API.

    Supported endpoints:

        GET  /api/v1/me
        GET  /api/v1/products
        POST /api/v1/order
        GET  /api/v1/orders
        GET  /api/v1/order/{id}
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 15,
    ):
        self.base_url = (
            base_url or RESELLER_API_URL
        ).rstrip("/")

        self.api_key = (
            api_key or RESELLER_API_KEY
        )

        self.timeout = aiohttp.ClientTimeout(
            total=timeout
        )

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ResellerAPIError(
                "Reseller API key is not configured."
            )

        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession(
                timeout=self.timeout
            ) as session:

                async with session.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json_data,
                    params=params,
                ) as response:

                    text = await response.text()

                    if response.status >= 400:
                        raise ResellerAPIError(
                            f"HTTP {response.status}: {text[:500]}"
                        )

                    try:
                        data = await response.json(
                            content_type=None
                        )
                    except Exception as exc:
                        raise ResellerAPIError(
                            f"Invalid JSON response: {text[:500]}"
                        ) from exc

                    if not isinstance(data, dict):
                        raise ResellerAPIError(
                            "Unexpected API response format."
                        )

                    return data

        except aiohttp.ClientError as exc:
            logger.exception(
                "Reseller API request failed: %s",
                url,
            )

            raise ResellerAPIError(
                f"Unable to connect to reseller API: {exc}"
            ) from exc

    async def get_profile(self) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/me",
        )

    async def get_products(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/api/v1/products",
        )

        services = data.get("services")

        if not isinstance(services, list):
            raise ResellerAPIError(
                "Reseller API returned invalid products data."
            )

        return services

    async def get_product(
        self,
        service_id: str,
    ) -> dict[str, Any] | None:

        products = await self.get_products()

        for product in products:

            if str(
                product.get("service_id")
            ) == str(service_id):

                return product

        return None

    async def create_order(
        self,
        service_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:

        if quantity < 1:
            raise ValueError(
                "Quantity must be at least 1."
            )

        return await self._request(
            "POST",
            "/api/v1/order",
            json_data={
                "service_id": service_id,
                "quantity": quantity,
            },
        )

    async def get_orders(
        self,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:

        if limit > 200:
            limit = 200

        return await self._request(
            "GET",
            "/api/v1/orders",
            params={
                "page": page,
                "limit": limit,
            },
        )

    async def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:

        return await self._request(
            "GET",
            f"/api/v1/order/{order_id}",
        )


reseller_api = ResellerAPI()