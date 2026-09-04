"""Apollo.io People Search. Search is free of credits but masks contact details."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.errors import PeopleProviderError
from app.integrations.people.base import PersonResult, SearchCriteria

log = structlog.get_logger()

_SENIORITY_MAP = {
    "entry": "entry",
    "junior": "entry",
    "senior": "senior",
    "lead": "head",
    "manager": "manager",
    "director": "director",
    "vp": "vp",
    "head": "head",
    "c-level": "c_suite",
    "cxo": "c_suite",
    "owner": "owner",
    "intern": "intern",
    "founder": "founder",
    "partner": "partner",
}


class ApolloProvider:
    name = "apollo"

    def __init__(self, api_key: str, *, base_url: str = "https://api.apollo.io/api/v1"):
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
            timeout=30,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def search(self, criteria: SearchCriteria) -> list[PersonResult]:
        body: dict[str, Any] = {"page": 1, "per_page": criteria.limit}
        if criteria.titles:
            body["person_titles"] = criteria.titles
        if criteria.locations:
            body["person_locations"] = criteria.locations
        if criteria.seniorities:
            mapped = sorted(
                {_SENIORITY_MAP.get(s.lower(), s.lower()) for s in criteria.seniorities}
            )
            body["person_seniorities"] = mapped
        keywords = " ".join([criteria.keywords, *criteria.skills]).strip()
        if keywords:
            body["q_keywords"] = keywords
        try:
            resp = await self._http.post("/mixed_people/api_search", json=body)
        except httpx.HTTPError as exc:
            raise PeopleProviderError(f"Apollo request failed: {exc}") from exc
        if resp.status_code >= 400:
            log.warning("apollo_error", status=resp.status_code, body=resp.text[:300])
            raise PeopleProviderError(
                f"Apollo returned HTTP {resp.status_code}",
                details={"upstreamStatus": resp.status_code, "upstream": resp.text[:500]},
            )
        people = resp.json().get("people", []) or []
        return [self._normalize(p) for p in people]

    @staticmethod
    def _normalize(p: dict[str, Any]) -> PersonResult:
        org = p.get("organization") or {}
        loc = ", ".join(x for x in [p.get("city"), p.get("state"), p.get("country")] if x)
        phone = None
        for num in p.get("phone_numbers") or []:
            if isinstance(num, dict) and num.get("sanitized_number"):
                phone = num["sanitized_number"]
                break
        email = p.get("email") if p.get("email") and "@" in str(p.get("email")) else None
        return PersonResult(
            source="apollo",
            source_ref=str(p.get("id")),
            name=p.get("name")
            or " ".join(x for x in [p.get("first_name"), p.get("last_name")] if x),
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            phone=phone,
            email=email,
            current_title=p.get("title"),
            current_company=org.get("name"),
            location=loc or None,
            skills=[],
            linkedin_url=p.get("linkedin_url"),
            summary=p.get("headline"),
        )
