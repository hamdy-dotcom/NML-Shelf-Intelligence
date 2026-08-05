"""
Salla Partner API client with mock/fixture mode.

Field names in _parse_product() are based on Salla's documented v2 API shape.
Verify these against live responses on the first real run and adjust if needed —
Salla's field names are sometimes camelCase in practice vs snake_case in docs.
"""
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from shared.config import settings

logger = logging.getLogger(__name__)

_LISTINGS_FIXTURE = Path(__file__).parent / "fixtures" / "sample_listings.json"


class RawListing(BaseModel):
    external_id: str
    store_name: str
    store_url: str
    listing_title_raw: str
    listing_image_url: str | None
    price: float | None
    currency: str = "SAR"


def _parse_product(raw: dict[str, Any], store_name: str, store_url: str) -> RawListing:
    price_obj = raw.get("price") or {}
    return RawListing(
        external_id=str(raw["id"]),
        store_name=store_name,
        store_url=store_url,
        listing_title_raw=raw.get("name", ""),
        listing_image_url=raw.get("thumbnail"),
        price=price_obj.get("amount") if isinstance(price_obj, dict) else None,
        currency=price_obj.get("currency", "SAR") if isinstance(price_obj, dict) else "SAR",
    )


class SallaClient:
    def __init__(
        self,
        store_name: str,
        store_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        mock_mode: bool = False,
    ) -> None:
        self.store_name = store_name
        self.store_url = store_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self.mock_mode = mock_mode
        self._access_token: str | None = None

    def _refresh_access_token(self) -> None:
        resp = httpx.post(
            settings.salla_token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._access_token = payload["access_token"]
        # Salla issues a new refresh token each time; persist it if needed
        if "refresh_token" in payload:
            self._refresh_token = payload["refresh_token"]
            logger.info("Salla refresh token rotated for store %s", self.store_name)

    def _get_access_token(self) -> str:
        if not self._access_token:
            self._refresh_access_token()
        return self._access_token  # type: ignore[return-value]

    def _fetch_live_listings(self) -> list[RawListing]:
        listings: list[RawListing] = []
        url: str | None = f"{settings.salla_api_base_url}/products"
        headers = {"Authorization": f"Bearer {self._get_access_token()}"}

        while url:
            resp = httpx.get(url, headers=headers, timeout=30)
            if resp.status_code == 401:
                # Token expired mid-run — refresh and retry once
                self._access_token = None
                self._refresh_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = httpx.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            body = resp.json()
            for product in body.get("data", []):
                listings.append(_parse_product(product, self.store_name, self.store_url))

            cursor = body.get("cursor", {})
            # Salla v2 cursor pagination — field names may vary; handle both cases
            has_more = cursor.get("has_more") or cursor.get("hasMore", False)
            url = (cursor.get("next_url") or cursor.get("nextUrl")) if has_more else None

        logger.info("Fetched %d listings from Salla store %s", len(listings), self.store_name)
        return listings

    def _load_mock_listings(self) -> list[RawListing]:
        fixture = json.loads(_LISTINGS_FIXTURE.read_text(encoding="utf-8"))
        listings: list[RawListing] = []
        for store_fixture in fixture.get("stores", []):
            if store_fixture["store_name"] != self.store_name:
                continue
            for product in store_fixture.get("products_response", {}).get("data", []):
                listings.append(
                    _parse_product(product, store_fixture["store_name"], store_fixture["store_url"])
                )
        logger.info("Loaded %d mock listings for store %s", len(listings), self.store_name)
        return listings

    def fetch_listings(self) -> list[RawListing]:
        if self.mock_mode:
            return self._load_mock_listings()
        return self._fetch_live_listings()


def get_salla_clients() -> list[SallaClient]:
    """
    Return one SallaClient per merchant store.

    MVP: single merchant from env vars, or all mock stores from fixture.
    Multi-merchant extension: replace with DB/config lookup of
    (store_name, store_url, refresh_token) per installed merchant app.
    """
    if settings.orbit_mock_mode:
        fixture = json.loads(_LISTINGS_FIXTURE.read_text(encoding="utf-8"))
        return [
            SallaClient(
                store_name=s["store_name"],
                store_url=s["store_url"],
                client_id="",
                client_secret="",
                refresh_token="",
                mock_mode=True,
            )
            for s in fixture.get("stores", [])
        ]
    return [
        SallaClient(
            store_name=settings.salla_store_name,
            store_url=settings.salla_store_url,
            client_id=settings.salla_client_id,
            client_secret=settings.salla_client_secret,
            refresh_token=settings.salla_refresh_token,
            mock_mode=False,
        )
    ]
