from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import ContainerDep
from app.core.errors import FeatureDisabled
from app.integrations.people.base import PersonResult, SearchCriteria
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

_LABELS = {
    "mock": (
        "Demo dataset",
        "Seeded profiles, no phone numbers; calls use the safe-dial test number.",
    ),
    "apollo": (
        "Apollo.io",
        "Free search; contact details are masked unless enrichment credits are used.",
    ),
    "pdl": (
        "People Data Labs",
        "Returns phone numbers where the dataset has them; costs credits per record.",
    ),
}


@router.get("/providers", response_model=list[ProviderInfoDto])
async def providers(c: ContainerDep) -> list[ProviderInfoDto]:
    out = []
    for name, (label, note) in _LABELS.items():
        out.append(
            ProviderInfoDto(name=name, configured=name in c.providers, label=label, note=note)
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
