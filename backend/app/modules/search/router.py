from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import ContainerDep
from app.core.errors import FeatureDisabled
from app.integrations.people.base import PersonResult, SearchCriteria
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


@router.get("/providers", response_model=list[ProviderInfoDto])
async def providers(c: ContainerDep) -> list[ProviderInfoDto]:
    out = []
    for name, (label, note) in _LABELS.items():
        provider = c.providers.get(name)
        # The sandbox returns synthetic people. Say so where the recruiter picks the source,
        # or a demo run against it looks like a real search that found fake candidates.
        if isinstance(provider, PdlProvider) and provider.sandbox:
            label = f"{label} (sandbox)"
            note = (
                "Synthetic records with the live schema, at zero credits. "
                "Set PDL_SANDBOX=false for real people."
            )
        out.append(
            ProviderInfoDto(name=name, configured=provider is not None, label=label, note=note)
        )
    return out


@router.post("/people", response_model=SearchPeopleResponse)
async def search_people(body: SearchPeopleRequest, c: ContainerDep) -> SearchPeopleResponse:
    provider = c.providers.get(body.provider)
    if provider is None:
        raise FeatureDisabled(f"Provider '{body.provider}' is not configured on this deployment.")
    results = await provider.search(SearchCriteria(**body.criteria.model_dump()))
    return SearchPeopleResponse(
        provider=body.provider, results=[PersonDto.model_validate(r.model_dump()) for r in results]
    )


@router.post("/import", response_model=list[CandidateDto], status_code=status.HTTP_201_CREATED)
async def import_people(body: ImportPeopleRequest, c: ContainerDep) -> list[CandidateDto]:
    people = [PersonResult.model_validate(p.model_dump()) for p in body.people]
    return await candidates.import_people(c.db, body.job_id, people)
