"""Wire-format tests: camelCase keys, error envelope, access code."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.config import Settings
from app.integrations.hunar.webhook import compute_signature, verify_signature
from app.modules.calls.schemas import CallDto
from app.modules.candidates.schemas import CandidateDto
from app.modules.jobs.schemas import JobDto


def _is_camel(key: str) -> bool:
    return "_" not in key and key[:1].islower()


def test_dtos_serialize_camel_case() -> None:
    now = datetime.now(UTC)
    job = JobDto(_id="j1", title="T", description="d" * 20, created_at=now, updated_at=now)
    cand = CandidateDto(_id="c1", job_id="j1", name="A", created_at=now, updated_at=now)
    call = CallDto(
        _id="k1",
        hunar_call_id="h",
        job_id="j1",
        candidate_id="c1",
        agent_id="a1",
        hunar_agent_id="ha",
        callee_name="A",
        dialed_number="+911",
        safe_dial=True,
        status="SCHEDULED",
        lifecycle_status="IN_PROGRESS",
        created_at=now,
        updated_at=now,
    )
    for dto in (job, cand, call):
        dumped = dto.model_dump(by_alias=True, mode="json")
        assert all(_is_camel(k) for k in dumped), dumped.keys()
        assert "id" in dumped and "_id" not in dumped
    assert (
        JobDto.model_validate(
            {
                "_id": "x",
                "title": "T",
                "description": "d" * 20,
                "created_at": now,
                "updated_at": now,
            }
        ).id
        == "x"
    )


def test_naive_mongo_datetimes_get_utc_offset() -> None:
    naive = datetime(2026, 9, 4, 12, 0, 0)
    dto = JobDto(_id="j", title="T", description="d" * 20, created_at=naive, updated_at=naive)
    created = dto.model_dump(by_alias=True, mode="json")["createdAt"]
    assert created.endswith("Z") or created.endswith("+00:00")


async def test_error_envelope_on_404(client: AsyncClient) -> None:
    resp = await client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "job_not_found"
    assert body["error"]["details"]["requestId"]
    assert resp.headers["x-request-id"] == body["error"]["details"]["requestId"]


async def test_validation_error_uses_same_envelope(client: AsyncClient) -> None:
    resp = await client.post("/api/jobs", json={"title": "x"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_failed"


async def test_unknown_field_is_rejected(client: AsyncClient) -> None:
    resp = await client.post("/api/jobs/parse", json={"description": "x" * 30, "bogus": 1})
    assert resp.status_code == 422


def test_settings_split_and_redact() -> None:
    s = Settings(
        env="test",
        cors_origins="http://a,http://b",
        hunar_api_key="secret",
        mongodb_uri="mongodb://x",
        app_access_code="not-the-real-code",
    )
    assert s.cors_origins == ["http://a", "http://b"]
    red = s.redact()
    assert red["hunar_api_key"] == "***" and red["mongodb_uri"] == "***"
    # The startup log prints this dict; the demo gate must not be readable from CloudWatch.
    assert red["app_access_code"] == "***"
    assert red["dial_code_ttl_minutes"] == 10, "numeric knobs named *code* stay readable"


def test_cors_origins_drop_a_pasted_trailing_slash() -> None:
    s = Settings(env="test", cors_origins="https://main.d1.amplifyapp.com/")  # type: ignore[call-arg]
    assert s.cors_origins == ["https://main.d1.amplifyapp.com"]


def test_webhook_signature_roundtrip() -> None:
    body = b'{"event_type":"call_status_updated"}'
    sig = compute_signature("k", "123", body)
    assert verify_signature("k", "123", sig, body)
    assert verify_signature("k", "123", "other," + sig, body)
    assert not verify_signature("k", "124", sig, body)
    assert not verify_signature("k", "123", None, body)


async def test_health_is_public(client: AsyncClient) -> None:
    assert (await client.get("/health")).json()["status"] == "ok"
