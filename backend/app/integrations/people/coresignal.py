"""Coresignal Multi-source Employee API.

Two steps, and the split matters for cost:
  POST /employee_multi_source/search/es_dsl   -> a list of employee ids   (free)
  GET  /employee_multi_source/collect/{id}    -> the full record          (20 credits each)

So a search is free to run and useless to display, and every row you actually show costs
20 credits. The 7-day trial carries 2,000, which is 100 profiles. `max_collect` is the
guard rail: it caps how much a single search can spend, whatever limit the caller asked for.

Endpoint paths, the `apikey` header and the record fields come from Coresignal's published
API docs. Unverified against a live key, because this project has none.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from app.core.errors import PeopleProviderError
from app.integrations.people.base import PersonResult, SearchCriteria

log = structlog.get_logger()

BASE_URL = "https://api.coresignal.com/cdapi/v2"
CREDITS_PER_PROFILE = 20


class CoresignalProvider:
    name = "coresignal"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        max_collect: int = 10,
        timeout: float = 30.0,
    ):
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"apikey": api_key, "Accept": "application/json"},
            timeout=timeout,
        )
        self._max_collect = max_collect

    async def aclose(self) -> None:
        await self._http.aclose()

    @staticmethod
    def build_query(criteria: SearchCriteria) -> dict[str, Any]:
        """Elasticsearch DSL over the multi-source employee index."""
        must: list[dict[str, Any]] = []
        should: list[dict[str, Any]] = []

        if criteria.titles:
            must.append(
                {
                    "bool": {
                        "should": [
                            {"match_phrase": {"active_experience_title": t}}
                            for t in criteria.titles
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if criteria.locations:
            must.append(
                {
                    "bool": {
                        "should": [{"match": {"location_full": loc}} for loc in criteria.locations],
                        "minimum_should_match": 1,
                    }
                }
            )
        for skill in criteria.skills:
            should.append({"match": {"inferred_skills": skill}})
        if criteria.keywords:
            should.append({"match": {"headline": criteria.keywords}})

        query: dict[str, Any] = {"bool": {"must": must or [{"match_all": {}}]}}
        if should:
            query["bool"]["should"] = should
        return {"query": query}

    async def _request(self, method: str, path: str, **kw: Any) -> Any:
        try:
            resp = await self._http.request(method, path, **kw)
        except httpx.HTTPError as exc:
            raise PeopleProviderError(f"Coresignal request failed: {exc}") from exc
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            log.warning("coresignal_error", status=resp.status_code, body=resp.text[:300])
            raise PeopleProviderError(
                f"Coresignal returned HTTP {resp.status_code}",
                details={"upstreamStatus": resp.status_code, "upstream": resp.text[:500]},
            )
        return resp.json() if resp.content else None

    async def search(self, criteria: SearchCriteria) -> list[PersonResult]:
        found = await self._request(
            "POST", "/employee_multi_source/search/es_dsl", json=self.build_query(criteria)
        )
        # The search returns bare ids; tolerate an envelope in case that changes.
        ids: list[Any] = found if isinstance(found, list) else (found or {}).get("data") or []
        if not ids:
            return []

        wanted = min(criteria.limit, self._max_collect)
        ids = ids[:wanted]
        log.info("coresignal_collect", profiles=len(ids), credits=len(ids) * CREDITS_PER_PROFILE)

        sem = asyncio.Semaphore(4)

        async def collect(employee_id: Any) -> dict[str, Any] | None:
            async with sem:
                record = await self._request("GET", f"/employee_multi_source/collect/{employee_id}")
                return record if isinstance(record, dict) else None

        records = await asyncio.gather(*(collect(i) for i in ids))
        return [self._normalize(r) for r in records if r]

    @staticmethod
    def _company(record: dict[str, Any]) -> str | None:
        """The record has no flat active-company name, so fall back through the experience list."""
        for key in ("active_experience_company_name", "company_name"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for job in record.get("experience") or []:
            if isinstance(job, dict):
                name = job.get("company_name")
                if isinstance(name, str) and name.strip():
                    return name
        shorthand = record.get("active_experience_company_shorthand_name")
        return shorthand if isinstance(shorthand, str) and shorthand else None

    @staticmethod
    def _normalize(r: dict[str, Any]) -> PersonResult:
        emails = r.get("professional_emails_collection") or []
        email = r.get("primary_professional_email")
        if not isinstance(email, str) and emails:
            first = emails[0]
            email = first.get("professional_email") if isinstance(first, dict) else first
        months = r.get("total_experience_duration_months")
        shorthand = r.get("active_experience_company_shorthand_name")
        return PersonResult(
            source="coresignal",
            source_ref=str(r.get("id")),
            name=(r.get("full_name") or "Unknown"),
            first_name=r.get("first_name") or None,
            last_name=r.get("last_name") or None,
            # Coresignal sells firmographic data, not dialable numbers.
            phone=None,
            email=email if isinstance(email, str) else None,
            current_title=r.get("active_experience_title") or None,
            current_company=CoresignalProvider._company(r),
            location=r.get("location_full") or r.get("location_country") or None,
            skills=[s for s in (r.get("inferred_skills") or []) if isinstance(s, str)][:15],
            linkedin_url=(
                f"https://www.linkedin.com/in/{shorthand}"
                if isinstance(shorthand, str) and shorthand
                else None
            ),
            summary=r.get("headline") or None,
            years_experience=round(months / 12, 1) if isinstance(months, int | float) else None,
        )
