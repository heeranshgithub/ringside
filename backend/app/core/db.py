"""Mongo access. Documents are pure snake_case and never leave the service layer as-is."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

Db = AsyncIOMotorDatabase
Doc = dict[str, Any]


def as_doc(raw: Mapping[str, Any]) -> Doc:
    """Motor hands back Mapping; the service layer works on plain dicts."""
    return dict(raw)


def make_client(uri: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(uri, uuidRepresentation="standard", serverSelectionTimeoutMS=5000)


async def ensure_indexes(db: Db) -> None:
    await db.jobs.create_index("created_at")
    await db.agents.create_index("hunar_agent_id", unique=True, sparse=True)
    await db.agents.create_index("job_id")
    await db.candidates.create_index("job_id")
    await db.candidates.create_index([("job_id", 1), ("source", 1), ("source_ref", 1)])
    await db.calls.create_index("hunar_call_id", unique=True, sparse=True)
    await db.calls.create_index("job_id")
    await db.calls.create_index("candidate_id")
    await db.calls.create_index("lifecycle_status")
    await db.calls.create_index("created_at")
    await db.dial_targets.create_index("session_id")
    await db.dial_targets.create_index("phone")
    await db.dial_targets.create_index("created_at")
    await db.dial_audit.create_index("at")
    await db.webhook_events.create_index("received_at")
    await db.webhook_events.create_index("hunar_call_id")
