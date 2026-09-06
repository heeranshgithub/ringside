"""People Data Labs Person Search (Elasticsearch DSL).

Search bills one credit per profile returned, and the free tier carries 100 a month.
The sandbox at sandbox.api.peopledatalabs.com serves synthetic records with an identical
schema at zero credits, which is what development and the offline demo should run against.

Free-tier caveat that bites: contact fields (mobile_phone, work_email, ...) come back as
booleans rather than values, so they are coerced to None instead of the string "True".
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.errors import PeopleProviderError
from app.integrations.people.base import PersonResult, SearchCriteria

log = structlog.get_logger()


PRODUCTION_URL = "https://api.peopledatalabs.com/v5"
SANDBOX_URL = "https://sandbox.api.peopledatalabs.com/v5"


class PdlProvider:
    name = "pdl"

    def __init__(self, api_key: str, *, sandbox: bool = False, base_url: str | None = None):
        self.sandbox = sandbox
        self._http = httpx.AsyncClient(
            base_url=base_url or (SANDBOX_URL if sandbox else PRODUCTION_URL),
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=30,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    @staticmethod
    def build_query(criteria: SearchCriteria) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should: list[dict[str, Any]] = []
        if criteria.titles:
            must.append(
                {
                    "bool": {
                        "should": [
                            {"match_phrase": {"job_title": t.lower()}} for t in criteria.titles
                        ],
                    }
                }
            )
        if criteria.locations:
            # PDL's location fields are keyword-typed: they hold a bare "gurugram", and a
            # `match` only fires on the whole value. Sending the model's "Gurugram, India"
            # therefore matched nothing and, because this clause is a `must`, zeroed every
            # search. Measured against the live API on 2026-09-06: the composite string
            # returned 0, while `term location_locality = gurugram` returned 777,632.
            # So keep the leading segment, which is the city, and try it as both a locality
            # and a region — "Karnataka" and "Bengaluru" both arrive in this list.
            places: list[dict[str, Any]] = []
            for loc in criteria.locations:
                city = next((p.strip().lower() for p in loc.split(",") if p.strip()), "")
                if not city:
                    continue
                places.append({"term": {"location_locality": city}})
                places.append({"term": {"location_region": city}})
            if places:
                must.append({"bool": {"should": places}})
        for s in criteria.skills:
            should.append({"term": {"skills": s.lower()}})
        if criteria.keywords:
            should.append({"match": {"summary": criteria.keywords}})
        q: dict[str, Any] = {"bool": {"must": must}}
        if should:
            q["bool"]["should"] = should
        return q

    async def search(self, criteria: SearchCriteria) -> list[PersonResult]:
        body = {
            "query": self.build_query(criteria),
            "size": criteria.limit,
            "dataset": "all",
            "pretty": False,
        }
        try:
            resp = await self._http.post("/person/search", json=body)
        except httpx.HTTPError as exc:
            raise PeopleProviderError(f"PDL request failed: {exc}") from exc
        if resp.status_code == 404:  # PDL uses 404 for "no matches"
            return []
        if resp.status_code >= 400:
            log.warning("pdl_error", status=resp.status_code, body=resp.text[:300])
            raise PeopleProviderError(
                f"PDL returned HTTP {resp.status_code}",
                details={"upstreamStatus": resp.status_code, "upstream": resp.text[:500]},
            )
        return [self._normalize(p) for p in resp.json().get("data", []) or []]

    @staticmethod
    def _text(*values: Any) -> str | None:
        """Gated fields arrive as booleans rather than values, so take the first real string.

        Verified against the sandbox: on a plan without contact or granular-location access,
        `mobile_phone`, `work_email` and `location_name` all come back as `True`.
        """
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _items(value: Any) -> list[Any]:
        """Gated list fields arrive as booleans too, and `iter(True)` raises."""
        return value if isinstance(value, list) else []

    @staticmethod
    def _normalize(p: dict[str, Any]) -> PersonResult:
        phone = PdlProvider._text(
            p.get("mobile_phone"), next(iter(PdlProvider._items(p.get("phone_numbers"))), None)
        )
        email = PdlProvider._text(
            p.get("work_email"), next(iter(PdlProvider._items(p.get("personal_emails"))), None)
        )
        exp = p.get("inferred_years_experience")
        return PersonResult(
            source="pdl",
            source_ref=str(p.get("id")),
            name=(PdlProvider._text(p.get("full_name")) or "").title() or "Unknown",
            first_name=PdlProvider._text(p.get("first_name")),
            last_name=PdlProvider._text(p.get("last_name")),
            phone=phone,
            email=email,
            current_title=PdlProvider._text(p.get("job_title")),
            current_company=PdlProvider._text(p.get("job_company_name")),
            location=PdlProvider._text(p.get("location_name"), p.get("location_country")),
            skills=[s for s in PdlProvider._items(p.get("skills")) if isinstance(s, str)][:15],
            linkedin_url=(
                f"https://{linkedin}"
                if (linkedin := PdlProvider._text(p.get("linkedin_url")))
                else None
            ),
            summary=PdlProvider._text(p.get("summary")),
            years_experience=float(exp) if isinstance(exp, int | float) else None,
        )
