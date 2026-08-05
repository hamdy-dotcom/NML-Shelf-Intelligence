"""
Meta Ad Library client — stub with mock mode.

Graph API endpoint: GET https://graph.facebook.com/v21.0/ads_archive
Required params: ad_reached_countries=SA, access_token=<token>
Docs: https://developers.facebook.com/docs/marketing-api/reference/ads-archive/

To activate:
1. Set META_AD_LIBRARY_ACCESS_TOKEN in .env
2. Implement _fetch_live_signals() using the ads_archive endpoint
3. Remove the NotImplementedError from fetch_ad_signals()
"""
import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_AD_SIGNALS_FIXTURE = Path(__file__).parent / "fixtures" / "sample_ad_signals.json"


class AdSignalData(BaseModel):
    search_term: str
    page_name: str | None = None
    ad_count_active: int


class MetaAdLibraryClient:
    def __init__(self, access_token: str, mock_mode: bool = False) -> None:
        self.access_token = access_token
        self.mock_mode = mock_mode

    def fetch_ad_signals(self, search_terms: list[str]) -> list[AdSignalData]:
        if self.mock_mode:
            return self._load_mock_signals()
        raise NotImplementedError(
            "Meta Ad Library live integration not yet implemented. "
            "See module docstring for activation steps."
        )

    def _load_mock_signals(self) -> list[AdSignalData]:
        fixture = json.loads(_AD_SIGNALS_FIXTURE.read_text(encoding="utf-8"))
        signals = [AdSignalData(**s) for s in fixture.get("meta_signals", [])]
        logger.info("Loaded %d mock Meta ad signals", len(signals))
        return signals
