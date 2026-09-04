"""People Data Labs Person Search (Elasticsearch DSL). Returns phones where the dataset has them."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.errors import PeopleProviderError
from app.integrations.people.base import PersonResult, SearchCriteria

log = structlog.get_logger()


class PdlProvider:
    name = "pdl"

    def __init__(self, api_key: str, *, base_url: str = "https://api.peopledatalabs.com/v5"):
        self._http = httpx.AsyncClient(
            base_url=base_url,
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
                        "minimum_should_match": 1,
                    }
                }
            )
        if criteria.locations:
            must.append(
                {
                    "bool": {
                        "should": [
                            {"match": {"location_name": loc.lower()}} for loc in criteria.locations
                        ]
                        + [
                            {"match": {"location_locality": loc.lower()}}
                            for loc in criteria.locations
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
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
    def _normalize(p: dict[str, Any]) -> PersonResult:
        phone = p.get("mobile_phone") or next(iter(p.get("phone_numbers") or []), None)
        email = p.get("work_email") or next(iter(p.get("personal_emails") or []), None)
        exp = p.get("inferred_years_experience")
        return PersonResult(
            source="pdl",
            source_ref=str(p.get("id")),
            name=(p.get("full_name") or "").title() or "Unknown",
            first_name=(p.get("first_name") or None),
            last_name=(p.get("last_name") or None),
            phone=phone,
            email=email,
            current_title=(p.get("job_title") or None),
            current_company=(p.get("job_company_name") or None),
            location=(p.get("location_name") or None),
            skills=list(p.get("skills") or [])[:15],
            linkedin_url=(f"https://{p['linkedin_url']}" if p.get("linkedin_url") else None),
            summary=p.get("summary"),
            years_experience=float(exp) if isinstance(exp, int | float) else None,
        )
