"""The rules that decide what this product is willing to ring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.core.errors import HunarApiError, ValidationFailed
from app.core.phone import assert_dialable, mask, normalize_phone, pretty
from app.integrations.hunar.client import FakeHunarClient
from app.main import create_app
from app.modules.calls.service import resolve_dial_number
from tests.stub_llm import StubLlm

SESSION = "session-abcdef123456"


# ---------- phone rules ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("098765-43210", "+919876543210"),
        ("(+91) 98765 43210", "+919876543210"),
        ("0091 98765 43210", "+919876543210"),
        ("+1 415 555 0100", "+14155550100"),
    ],
)
def test_normalize_accepts_what_people_type(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["12345", "abcdef", "+91 98765"])
def test_normalize_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValidationFailed):
        normalize_phone(raw)


def test_normalize_passes_through_empty() -> None:
    assert normalize_phone("") is None
    assert normalize_phone(None) is None


@pytest.mark.parametrize("number", ["+915876543210", "+911234567890", "+919999999999"])
def test_undialable_indian_numbers_are_refused(number: str) -> None:
    # a 5 prefix is not a mobile; 1234567890 starts with 1; all-nines is a single digit
    with pytest.raises(ValidationFailed):
        assert_dialable(number)


def test_dialable_indian_mobile_passes() -> None:
    assert assert_dialable("+919876543210") == "+919876543210"


@pytest.mark.parametrize("number", ["+14155550123", "+447700900123"])
def test_numbers_outside_india_are_refused(number: str) -> None:
    """The form promises Indian mobiles; an international call would surprise someone's bill."""
    with pytest.raises(ValidationFailed, match=r"\+91"):
        assert_dialable(number)


def test_mask_and_pretty() -> None:
    assert mask("+919876543210") == "+91" + "•" * 7 + "210"
    assert pretty("+919876543210") == "+91 98765 43210"


# ---------- which number actually rings ----------


def _settings(**kw: object) -> Settings:
    """Settings built from nothing but these values.

    `_env_file=None` matters: without it pydantic-settings reads the developer's real
    backend/.env, and a test asserting "no access code is configured" quietly starts
    passing or failing depending on whose machine it runs on.
    """
    base: dict[str, object] = {
        "env": "test",
        "mongodb_uri": "mongodb://unused",
        "hunar_api_key": "k",
        "test_phone_numbers": "+919999900000",
        "app_access_code": "",
        "allow_client_dial_target": False,
        "safe_dial_mode": True,
    }
    return Settings(_env_file=None, **{**base, **kw})  # type: ignore[arg-type]


def test_safe_dial_uses_the_server_number_by_default() -> None:
    number, safe, source = resolve_dial_number({"phone": "+919876543210"}, _settings())
    assert (number, safe, source) == ("+919999900000", True, "env")


def test_a_verified_session_number_wins_over_the_server_one() -> None:
    number, safe, source = resolve_dial_number(
        {"phone": "+919876543210"}, _settings(), verified_target="+918888800000"
    )
    assert (number, safe, source) == ("+918888800000", True, "session")


def test_the_candidates_own_number_is_never_reached_while_safe_dial_is_on() -> None:
    number, _, source = resolve_dial_number(
        {"phone": "+919876543210", "allow_real_dial": True}, _settings()
    )
    assert number == "+919999900000" and source == "env"


def test_real_dialling_needs_both_the_global_switch_and_the_candidate_flag() -> None:
    off = _settings(safe_dial_mode=False)
    number, safe, source = resolve_dial_number(
        {"phone": "+919876543210", "allow_real_dial": True}, off
    )
    assert (number, safe, source) == ("+919876543210", False, "real")

    number, safe, source = resolve_dial_number({"phone": "+919876543210"}, off)
    assert source == "env" and safe is True


def test_no_number_anywhere_is_an_error_not_a_silent_call() -> None:
    with pytest.raises(ValidationFailed):
        resolve_dial_number({"phone": "+919876543210"}, _settings(test_phone_numbers=""))


# ---------- the feature refuses to arm itself unsafely ----------


def test_client_dialling_will_not_enable_without_an_access_code() -> None:
    unguarded = _settings(allow_client_dial_target=True)
    assert unguarded.client_dial_enabled is False
    assert "APP_ACCESS_CODE" in (unguarded.client_dial_blocked_reason or "")

    guarded = _settings(allow_client_dial_target=True, app_access_code="secret")
    assert guarded.client_dial_enabled is True
    assert guarded.client_dial_blocked_reason is None


# ---------- the verification round trip ----------


@asynccontextmanager
async def _client(hunar: FakeHunarClient, **kw: object) -> AsyncIterator[AsyncClient]:
    """A live app: the lifespan is what builds the container the routes depend on."""
    settings = _settings(
        **{
            "allow_client_dial_target": True,
            "app_access_code": "secret",
            "poller_enabled": False,
            **kw,
        }
    )
    app = create_app(settings, db=AsyncMongoMockClient()["t"], hunar=hunar, llm=StubLlm())
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://t",
            headers={"X-Access-Code": "secret", "X-Session-Id": SESSION},
        ) as client,
    ):
        yield client


async def test_a_number_is_only_dialable_after_the_code_comes_back() -> None:
    hunar = FakeHunarClient()
    async with _client(hunar) as app_client:
        started = await app_client.post(
            "/api/dial-target/start", json={"phone": "98765 43210", "consent": True}
        )
        assert started.status_code == 201, started.text
        target = started.json()
        assert target["verified"] is False
        assert target["phoneMasked"] == mask("+919876543210")

        # the verification call went out to the number itself, not to the server's test line
        placed = list(hunar.calls.values())[-1]
        assert placed["mobile_number"] == "+919876543210"

        # nothing is dialable yet
        assert (await app_client.get("/api/dial-target/current")).json() is None

        wrong = await app_client.post(
            f"/api/dial-target/{target['id']}/confirm", json={"code": "0000"}
        )
        assert wrong.status_code == 400
        assert wrong.json()["error"]["code"] == "verification_failed"

        code = placed["custom_data"]["code"].replace(" ", "")
        ok = await app_client.post(f"/api/dial-target/{target['id']}/confirm", json={"code": code})
        assert ok.status_code == 200, ok.text
        assert ok.json()["verified"] is True

        current = (await app_client.get("/api/dial-target/current")).json()
        assert current["verified"] is True and current["phonePretty"] == "+91 98765 43210"


async def test_consent_is_required_before_we_ring_anyone() -> None:
    hunar = FakeHunarClient()
    async with _client(hunar) as app_client:
        resp = await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543210", "consent": False}
        )
        assert resp.status_code == 422
        assert hunar.calls == {}


async def test_verification_calls_are_capped_per_number() -> None:
    hunar = FakeHunarClient()
    async with _client(hunar, dial_verify_per_number_per_day=2) as app_client:
        for _ in range(2):
            assert (
                await app_client.post(
                    "/api/dial-target/start", json={"phone": "9876543210", "consent": True}
                )
            ).status_code == 201
        blocked = await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543210", "consent": True}
        )
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "rate_limited"


async def test_a_global_cap_bounds_the_day_across_every_number() -> None:
    """The per-number and per-session caps both scale with how many numbers are used.

    This is the only one that does not, so it is the real bound on a day's spend.
    """
    hunar = FakeHunarClient()
    async with _client(hunar, dial_verify_global_per_day=2) as app_client:
        for phone in ("9876543210", "9876543211"):
            assert (
                await app_client.post(
                    "/api/dial-target/start", json={"phone": phone, "consent": True}
                )
            ).status_code == 201
        # A third, untouched number: its own count is zero, and it is still refused.
        blocked = await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543212", "consent": True}
        )
        assert blocked.status_code == 429
        assert "today" in blocked.json()["error"]["message"]
        assert len(hunar.calls) == 2


async def test_the_counter_shows_the_limit_that_will_actually_stop_you() -> None:
    """It is the lower of the caps, not the friendlier one.

    A counter that says "4 left" and then refuses is worse than no counter at all.
    """
    hunar = FakeHunarClient()
    async with _client(
        hunar, dial_verify_global_per_day=2, dial_verify_per_session_per_day=5
    ) as app_client:
        assert (await app_client.get("/api/dial-target")).json()["verifyCallsLeftToday"] == 2
        await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543210", "consent": True}
        )
        assert (await app_client.get("/api/dial-target")).json()["verifyCallsLeftToday"] == 1


async def test_a_call_hunar_refuses_does_not_spend_a_slot() -> None:
    """The row is written before the call, so a failed call must take it back.

    Nobody heard a code, so nothing was verified and nothing should be charged against
    the day's caps.
    """
    hunar = FakeHunarClient()

    async def refuse(_: object) -> None:
        raise HunarApiError(400, "mobile_number: Invalid phone number")

    async with _client(hunar, dial_verify_global_per_day=2) as app_client:
        hunar.create_call = refuse  # type: ignore[method-assign]
        failed = await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543210", "consent": True}
        )
        assert failed.status_code >= 400
        # The allowance is untouched, so the visitor can simply try again.
        assert (await app_client.get("/api/dial-target")).json()["verifyCallsLeftToday"] == 2


async def test_the_flow_is_closed_when_the_flag_is_off() -> None:
    hunar = FakeHunarClient()
    async with _client(hunar, allow_client_dial_target=False) as app_client:
        assert (await app_client.get("/api/dial-target")).json()["enabled"] is False
        resp = await app_client.post(
            "/api/dial-target/start", json={"phone": "9876543210", "consent": True}
        )
        assert resp.status_code == 503
        assert hunar.calls == {}
