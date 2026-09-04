"""Base models: the camelCase wire boundary lives here and nowhere else."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for every model that touches the network."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class StrictApiModel(ApiModel):
    """Request bodies: unknown fields are a 422, not a silent no-op."""

    model_config = ConfigDict(extra="forbid", **ApiModel.model_config)


def _to_str(v: Any) -> Any:
    return str(v) if v is not None else v


MongoId = Annotated[str, BeforeValidator(_to_str)]


def _awareify(value: Any) -> Any:
    """Mongo hands back naive UTC datetimes; the wire must carry an offset."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if isinstance(value, dict):
        return {k: _awareify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_awareify(v) for v in value]
    return value


class MongoModel(ApiModel):
    """Response DTO backed by a Mongo document. `_id` reaches the wire as `id`."""

    id: MongoId | None = Field(
        default=None, validation_alias=AliasChoices("_id", "id"), serialization_alias="id"
    )

    @model_validator(mode="before")
    @classmethod
    def _fix_naive_datetimes(cls, data: Any) -> Any:
        return _awareify(data) if isinstance(data, dict) else data


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


def parse_upstream_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
