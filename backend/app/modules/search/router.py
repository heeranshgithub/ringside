from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import ContainerDep
from app.core.errors import FeatureDisabled
from app.integrations.people.base import PeopleProvider, PersonResult, SearchCriteria
from app.integrations.people.pdl import PdlProvider
from app.modules.candidates import service as candidates
from app.modules.candidates.schemas import CandidateDto
from app.modules.search.schemas import (
    ImportPeopleRequest,
    PersonDto,
    ProviderInfoDto,
    SearchPeopleRequest,
    SearchPeopleResponse,
)

router = APIRouter(prefix="/search", tags=["search"])

# Shown under the provider picker, so keep these true rather than flattering.
# Ringside never dials a sourced number: safe-dial sends every call to the number the visitor
# verified, so a provider is judged on whether its *search* is real and affordable, not on contacts.
_LABELS = {
    "mock": (
        "Demo dataset",
        "30 seeded profiles, no account needed. Use this unless you are showing a real source.",
    ),
    "pdl": (
        "People Data Labs",
        "100 free searches a month, 1 credit per profile. Sandbox mode costs nothing.",
    ),
    "coresignal": (
        "Coresignal",
        "Search is free; each profile shown costs 20 credits. The 7-day trial carries 2,000.",
    ),
    "apollo": (
        "Apollo.io",
        "Searching costs no credits, but API access is plan-gated and names arrive masked.",
    ),
}


def _result_cap(provider: PeopleProvider | None) -> int | None:
    """How many records one search may return, when each record is billed.

    Live PDL charges a credit per record and the free plan holds 100 a month, so one search
    at the picker's 50 spends half of them. One record is enough to show the source is real;
    the sandbox and the demo dataset are there for volume.
    """
    if isinstance(provider, PdlProvider) and not provider.sandbox:
        return 1
    return None


@router.get("/providers", response_model=list[ProviderInfoDto])
async def providers(c: ContainerDep) -> list[ProviderInfoDto]:
    out = []
    for name, (label, note) in _LABELS.items():
        provider = c.providers.get(name)
        cap = _result_cap(provider)
        # These notes face the recruiter, not the operator: nothing here may tell them to set
        # an environment variable they cannot reach.
        if isinstance(provider, PdlProvider) and provider.sandbox:
            label = f"{label} (sandbox)"
            note = "Synthetic records with the live schema. No credits are used."
        elif cap == 1:
            note = "Live data. Each record returned costs a credit, so a search brings back one."
        out.append(
            ProviderInfoDto(
                name=name, configured=provider is not None, label=label, note=note, max_results=cap
            )
        )
    return out


@router.post("/people", response_model=SearchPeopleResponse)
async def search_people(body: SearchPeopleRequest, c: ContainerDep) -> SearchPeopleResponse:
    provider = c.providers.get(body.provider)
    if provider is None:
        raise FeatureDisabled(f"Provider '{body.provider}' is not configured on this deployment.")
    criteria = body.criteria.model_dump()
    cap = _result_cap(provider)
    if cap is not None:
        criteria["limit"] = min(criteria["limit"], cap)
    results = await provider.search(SearchCriteria(**criteria))
    return SearchPeopleResponse(
        provider=body.provider, results=[PersonDto.model_validate(r.model_dump()) for r in results]
    )


@router.post("/import", response_model=list[CandidateDto], status_code=status.HTTP_201_CREATED)
async def import_people(body: ImportPeopleRequest, c: ContainerDep) -> list[CandidateDto]:
    people = [PersonResult.model_validate(p.model_dump()) for p in body.people]
    return await candidates.import_people(c.db, body.job_id, people)
