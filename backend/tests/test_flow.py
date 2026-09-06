"""End-to-end product flow against the fake Hunar client and in-memory Mongo."""

from __future__ import annotations

import json

from httpx import AsyncClient

from app.integrations.hunar.client import FakeHunarClient
from app.integrations.hunar.webhook import compute_signature
from tests.conftest import (
    TEST_KEY,
    make_agent,
    make_candidate,
    make_job,
    verify_dial_target,
)


async def test_parse_job_returns_criteria(client: AsyncClient) -> None:
    """The route wires the model's answer through to the DTO.

    This asserts plumbing, not parsing quality: the app owns no parser of its own, so the
    values here are whatever the injected model returned.
    """
    resp = await client.post(
        "/api/jobs/parse",
        json={"description": "Senior Python developer in Bengaluru with FastAPI and AWS. " * 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Senior Frontend Engineer (Next.js)"
    assert body["company"] == "Northline Labs"
    assert body["location"] == "Bengaluru"
    assert body["searchCriteria"]["skills"] == ["react", "typescript"]
    assert body["searchCriteria"]["locations"] == ["Bengaluru"]


async def test_job_agent_candidate_call_roundtrip(
    client: AsyncClient, hunar: FakeHunarClient
) -> None:
    job = await make_job(client)
    agent = await make_agent(client, job["id"])
    assert agent["hunarAgentId"] in hunar.agents
    assert set(agent["customVariables"]) == {"candidate_name", "job_role", "company", "location"}
    job = (await client.get(f"/api/jobs/{job['id']}")).json()
    assert job["agentId"] == agent["id"] and job["status"] == "active"

    cand = await make_candidate(client, job["id"])
    assert cand["phone"] == "+919876543210"

    # Safe dial needs a destination somebody proved is theirs; there is no server-side default.
    mine = await verify_dial_target(client, hunar, "99999 00000")

    launch = await client.post(
        "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
    )
    assert launch.status_code == 201, launch.text
    body = launch.json()
    assert body["skipped"] == []
    call = body["calls"][0]
    assert call["safeDial"] is True
    assert call["dialedNumber"] == mine
    assert call["targetNumber"] == "+919876543210"
    assert call["customData"]["candidate_name"] == "Ananya Iyer"
    assert call["customData"]["company"] == "Acme"

    upstream = hunar.calls[call["hunarCallId"]]
    assert upstream["mobile_number"] == "+919999900000"

    synced = (await client.post(f"/api/calls/{call['id']}/sync")).json()
    assert synced["status"] == "COMPLETED"
    assert synced["engagementStatus"] == "ENGAGED"
    assert synced["result"]["summary"]
    assert synced["assessment"]["fitScore"] >= 0
    assert [e["kind"] for e in synced["events"]] == ["created", "status", "recording", "result"]

    listed = (await client.get("/api/calls", params={"jobId": job["id"]})).json()
    assert listed["total"] == 1 and listed["items"][0]["id"] == call["id"]

    cand_after = (await client.get("/api/candidates", params={"jobId": job["id"]})).json()[0]
    assert cand_after["latestCallStatus"] == "COMPLETED"

    summary = (await client.get("/api/dashboard/summary")).json()
    assert summary["callsTotal"] == 1 and summary["engaged"] == 1


async def test_launch_without_a_verified_number_skips_and_says_why(
    client: AsyncClient, hunar: FakeHunarClient
) -> None:
    """The session target is what a launch dials, so the route must actually read it.

    It did not, for a while: `launch` never passed `verified_target`, and an operator-configured
    test number underneath meant every call still went somewhere. The fallback is gone, so the
    omission is now visible instead of silent.
    """
    job = await make_job(client)
    await make_agent(client, job["id"])
    cand = await make_candidate(client, job["id"])

    body = (
        await client.post(
            "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
        )
    ).json()
    assert body["calls"] == []
    assert "Verify your own number" in body["skipped"][0]["reason"]
    assert hunar.calls == {}, "nothing was dialled"

    # And once a number is proved, the same launch reaches it.
    mine = await verify_dial_target(client, hunar)
    body = (
        await client.post(
            "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
        )
    ).json()
    assert body["skipped"] == []
    assert body["calls"][0]["dialedNumber"] == mine


async def test_launch_skips_candidates_without_agent(client: AsyncClient) -> None:
    job = await make_job(client)
    cand = await make_candidate(client, job["id"])
    resp = await client.post(
        "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_failed"


async def test_csv_import(client: AsyncClient) -> None:
    job = await make_job(client)
    csv_text = (
        "name,phone,email,title,skills\n"
        "Rohan Mehta,+91 98765 00001,r@x.com,Frontend Dev,react;typescript\n"
        ",123,,,\n"
        "Bad Phone,12,,,"
    )
    resp = await client.post(
        "/api/candidates/import-csv", json={"jobId": job["id"], "csvText": csv_text}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["created"]) == 1
    assert body["created"][0]["phone"] == "+919876500001"
    assert body["created"][0]["skills"] == ["react", "typescript"]
    assert len(body["skipped"]) == 2


async def test_people_search_and_import(client: AsyncClient) -> None:
    job = await make_job(client)
    resp = await client.post(
        "/api/search/people",
        json={
            "provider": "mock",
            "criteria": {
                "titles": ["Frontend Engineer"],
                "skills": ["react", "next.js"],
                "locations": ["Bengaluru"],
                "limit": 5,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert results and results[0]["source"] == "mock"
    assert results[0]["phone"] is None
    imported = await client.post(
        "/api/search/import", json={"jobId": job["id"], "people": results[:2]}
    )
    assert imported.status_code == 201
    assert len(imported.json()) == 2
    again = await client.post(
        "/api/search/import", json={"jobId": job["id"], "people": results[:2]}
    )
    assert {c["id"] for c in again.json()} == {c["id"] for c in imported.json()}  # deduped
    providers = (await client.get("/api/search/providers")).json()
    assert {p["name"]: p["configured"] for p in providers} == {
        "mock": True,
        "pdl": False,
        "coresignal": False,
        "apollo": False,
    }


async def test_unconfigured_provider_is_503(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/search/people", json={"provider": "pdl", "criteria": {"titles": ["x"]}}
    )
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "feature_disabled"


async def test_webhook_updates_call(client: AsyncClient, hunar: FakeHunarClient) -> None:
    hunar.auto_complete = False
    job = await make_job(client)
    await make_agent(client, job["id"])
    cand = await make_candidate(client, job["id"])
    await verify_dial_target(client, hunar)
    call = (
        await client.post(
            "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
        )
    ).json()["calls"][0]

    payload = {
        "event_type": "call_summary",
        "call_id": call["hunarCallId"],
        "status": "COMPLETED",
        "lifecycle_status": "COMPLETED",
        "recording_url": "https://example.invalid/r.wav",
        "result": {"summary": "Great fit", "interested": True, "recommendation": "hire_now"},
    }
    body = json.dumps(payload).encode()
    ts = "1700000000"
    headers = {
        "X-Hunar-Timestamp": ts,
        "X-Hunar-Signature": compute_signature(TEST_KEY, ts, body),
        "Content-Type": "application/json",
    }
    resp = await client.post("/webhooks/hunar", content=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"received": True, "matched": True, "signatureValid": True}

    updated = (await client.get(f"/api/calls/{call['id']}")).json()
    assert updated["status"] == "COMPLETED"
    assert updated["recordingUrl"] == "https://example.invalid/r.wav"
    assert updated["assessment"]["recommendation"] in {"strong_yes", "yes"}
    assert updated["events"][-1]["source"] == "webhook"

    bad = await client.post(
        "/webhooks/hunar", content=body, headers={**headers, "X-Hunar-Signature": "nope"}
    )
    assert bad.json()["signatureValid"] is False


async def test_a_second_agent_with_the_same_name_is_numbered(client: AsyncClient) -> None:
    """Every demo visitor drafts from the same sample JD, and the draft names the agent
    after the job. Two identical names in the attach-existing picker cannot be told apart,
    so the second one is numbered before it is created on Hunar."""
    job = await make_job(client)
    first = await make_agent(client, job["id"])
    second = await make_agent(client, job["id"])
    third = await make_agent(client, job["id"])
    assert second["name"] == f"{first['name']} (2)"
    assert third["name"] == f"{first['name']} (3)"


async def test_agent_update_and_import(client: AsyncClient, hunar: FakeHunarClient) -> None:
    job = await make_job(client)
    agent = await make_agent(client, job["id"])
    upd = await client.patch(
        f"/api/agents/{agent['id']}", json={"name": "Renamed screener", "voicePersona": "ROY"}
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["name"] == "Renamed screener" and upd.json()["voicePersona"] == "ROY"
    bad = await client.patch(f"/api/agents/{agent['id']}", json={"voicePersona": "NOBODY"})
    assert bad.status_code == 422

    imported = await client.post("/api/agents/import", json={"hunarAgentId": agent["hunarAgentId"]})
    assert imported.status_code == 201
    assert imported.json()["id"] == agent["id"]  # upserted onto the existing mirror


async def test_access_code_gate(hunar: FakeHunarClient) -> None:
    from httpx import ASGITransport, AsyncClient
    from mongomock_motor import AsyncMongoMockClient

    from app.core.config import Settings
    from app.main import create_app
    from tests.stub_llm import StubLlm

    s = Settings(
        env="test",
        mongodb_uri="mongodb://x",
        hunar_api_key="k",
        app_access_code="open-sesame",
        poller_enabled=False,
    )
    app = create_app(s, db=AsyncMongoMockClient()["t"], hunar=hunar, llm=StubLlm())
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        assert (await c.get("/api/jobs")).status_code == 401
        assert (
            await c.get("/api/jobs", headers={"X-Access-Code": "open-sesame"})
        ).status_code == 200
        assert (await c.get("/health")).status_code == 200


async def test_a_second_launch_while_the_first_call_is_in_flight_is_skipped(
    client: AsyncClient, hunar: FakeHunarClient
) -> None:
    job = await make_job(client)
    await make_agent(client, job["id"])
    cand = await make_candidate(client, job["id"])
    await verify_dial_target(client, hunar, "99999 00000")
    first = await client.post(
        "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
    )
    assert first.status_code == 201 and first.json()["skipped"] == []

    again = await client.post(
        "/api/calls/launch", json={"jobId": job["id"], "candidateIds": [cand["id"]]}
    )
    body = again.json()
    assert body["calls"] == []
    assert "already in flight" in body["skipped"][0]["reason"]
