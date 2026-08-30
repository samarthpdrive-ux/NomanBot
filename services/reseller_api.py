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
        auth_type: str | None = None,
        auth_header: str | None = None,
        products_endpoint: str | None = None,
        balance_endpoint: str | None = None,
        order_endpoint: str | None = None,
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

        is_canboso = "canboso.com" in self.base_url.lower()

        self.auth_type = auth_type or ("bearer" if is_canboso else "header")
        self.auth_header = auth_header or "X-API-Key"

        if is_canboso:
            self.products_endpoint = products_endpoint or "/api/v2/telegram-buyer/products"
            self.balance_endpoint = balance_endpoint or "/api/v2/telegram-buyer/balance"
            self.order_endpoint = order_endpoint or "/api/v2/telegram-buyer/purchase"
        else:
            self.products_endpoint = products_endpoint or "/api/v1/products"
            self.balance_endpoint = balance_endpoint or "/api/v1/me"
            self.order_endpoint = order_endpoint or "/api/v1/order"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ResellerAPIError(
                "Reseller API key is not configured."
            )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.auth_type.lower() == "bearer":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers[self.auth_header] = self.api_key

        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:

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
        data = await self._request(
            "GET",
            self.balance_endpoint,
        )
        if isinstance(data, dict):
            return data
        return {"balance": data}

    async def get_balance(self) -> Any:
        data = await self._request(
            "GET",
            self.balance_endpoint,
        )
        if isinstance(data, dict):
            for key in ("balance", "funds", "credits", "wallet", "amount", "user_balance"):
                if key in data:
                    return data[key]
            return data.get("data", data)
        return data

    async def get_products(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            self.products_endpoint,
        )

        items_list = None
        if isinstance(data, list):
            items_list = data
        elif isinstance(data, dict):
            for key in ("services", "products", "items", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    items_list = val
                    break
            if items_list is None:
                for val in data.values():
                    if isinstance(val, list):
                        items_list = val
                        break

        if not isinstance(items_list, list):
            raise ResellerAPIError(
                "Reseller API returned invalid products data."
            )

        normalized = []
        for item in items_list:
            if not isinstance(item, dict):
                continue
            product = dict(item)
            if "service_id" not in product:
                for id_key in ("id", "product_id", "service", "code"):
                    if id_key in product:
                        product["service_id"] = product[id_key]
                        break
            if "name" not in product:
                for name_key in ("title", "product_name", "service_name"):
                    if name_key in product:
                        product["name"] = product[name_key]
                        break
            normalized.append(product)

        return normalized

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

        is_canboso = "canboso.com" in self.base_url.lower()
        payload = {
            "quantity": quantity,
        }
        if is_canboso:
            payload["product_id"] = service_id
        else:
            payload["service_id"] = service_id
            payload["product_id"] = service_id

        return await self._request(
            "POST",
            self.order_endpoint,
            json_data=payload,
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
