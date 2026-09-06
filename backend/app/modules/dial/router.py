from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, status

from app.core.deps import DbDep, HunarDep, SettingsDep
from app.core.errors import ValidationFailed
from app.modules.dial import service
from app.modules.dial.schemas import (
    ConfirmVerificationRequest,
    DialCapabilityDto,
    DialTargetDto,
    StartVerificationRequest,
)

router = APIRouter(prefix="/dial-target", tags=["dial"])

SessionId = Annotated[str | None, Header(alias="X-Session-Id")]


def _session(session_id: str | None) -> str:
    """The browser identifies itself so a verified number stays scoped to one visitor.

    Not an identity claim and not treated as one: it decides which number *this* browser
    may ring, never who anyone is. The real limits are per phone number, which a new
    session id cannot reset.
    """
    if not session_id or len(session_id) < 12:
        raise ValidationFailed("Missing session identifier.")
    return session_id


@router.get("", response_model=DialCapabilityDto)
async def capability(
    db: DbDep, settings: SettingsDep, x_session_id: SessionId = None
) -> DialCapabilityDto:
    if not settings.allow_client_dial_target:
        return DialCapabilityDto(enabled=False, reason=None)
    if not settings.client_dial_enabled:
        return DialCapabilityDto(enabled=False, reason=settings.client_dial_blocked_reason)

    left = await service.calls_left_today(db, settings, x_session_id)
    return DialCapabilityDto(enabled=True, reason=None, verify_calls_left_today=left)


@router.get("/current", response_model=DialTargetDto | None)
async def current(
    db: DbDep, settings: SettingsDep, x_session_id: SessionId = None
) -> DialTargetDto | None:
    if not x_session_id:
        return None
    doc = await service.current_target(db, x_session_id)
    payload = service.to_dto(doc, settings)
    return DialTargetDto.model_validate(payload) if payload else None


@router.post("/start", response_model=DialTargetDto, status_code=status.HTTP_201_CREATED)
async def start(
    body: StartVerificationRequest,
    db: DbDep,
    hunar: HunarDep,
    settings: SettingsDep,
    x_session_id: SessionId = None,
) -> DialTargetDto:
    doc = await service.start_verification(
        db,
        hunar,
        settings,
        phone_raw=body.phone,
        consent=body.consent,
        session_id=_session(x_session_id),
    )
    return DialTargetDto.model_validate(service.to_dto(doc, settings))


@router.post("/{id}/confirm", response_model=DialTargetDto)
async def confirm(
    id: str,
    body: ConfirmVerificationRequest,
    db: DbDep,
    settings: SettingsDep,
    x_session_id: SessionId = None,
) -> DialTargetDto:
    doc = await service.confirm_verification(
        db, settings, target_id=id, code=body.code, session_id=_session(x_session_id)
    )
    return DialTargetDto.model_validate(service.to_dto(doc, settings))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def release(db: DbDep, x_session_id: SessionId = None) -> None:
    if x_session_id:
        await service.release_target(db, x_session_id)
