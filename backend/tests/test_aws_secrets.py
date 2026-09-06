"""The Secrets Manager -> os.environ loader, with the AWS SDK stubbed so no call is ever made."""

from __future__ import annotations

import json
import os
import sys
import types
from collections.abc import Callable

import pytest

from app.core.aws_secrets import SECRETS_ID_VAR, SecretsLoadError, load_aws_secrets

SECRET = "arn:aws:secretsmanager:ap-south-1:123456789012:secret:ringside-backend/config-AbCdEf"


class _FakeClient:
    def __init__(self, *, payload: str | None = None, error: Exception | None = None):
        self._payload = payload
        self._error = error
        self.region: str | None = None

    def get_secret_value(self, SecretId: str) -> dict[str, str]:  # boto3 signature
        if self._error is not None:
            raise self._error
        return {} if self._payload is None else {"SecretString": self._payload}


@pytest.fixture
def fake_boto3(monkeypatch: pytest.MonkeyPatch) -> Callable[[_FakeClient], _FakeClient]:
    def _install(client: _FakeClient) -> _FakeClient:
        boto3 = types.ModuleType("boto3")

        def _client(service: str, region_name: str | None = None) -> _FakeClient:
            client.region = region_name
            return client

        boto3.client = _client  # type: ignore[attr-defined]
        botocore = types.ModuleType("botocore")
        exceptions = types.ModuleType("botocore.exceptions")

        class BotoCoreError(Exception): ...

        class ClientError(Exception): ...

        exceptions.BotoCoreError = BotoCoreError  # type: ignore[attr-defined]
        exceptions.ClientError = ClientError  # type: ignore[attr-defined]
        botocore.exceptions = exceptions  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "boto3", boto3)
        monkeypatch.setitem(sys.modules, "botocore", botocore)
        monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)
        return client

    return _install


def test_no_secret_id_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SECRETS_ID_VAR, raising=False)
    assert load_aws_secrets() == []


def test_blank_secret_id_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SECRETS_ID_VAR, "   ")
    assert load_aws_secrets() == []


def test_loads_keys_into_environ(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    fake_boto3(_FakeClient(payload=json.dumps({"MONGODB_DB": "ringside", "LOG_LEVEL": "DEBUG"})))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)
    monkeypatch.delenv("MONGODB_DB", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert sorted(load_aws_secrets()) == ["LOG_LEVEL", "MONGODB_DB"]
    assert os.environ["MONGODB_DB"] == "ringside"
    assert os.environ["LOG_LEVEL"] == "DEBUG"


def test_region_is_read_from_the_arn(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    """boto3 will not infer a region from an ARN; a bare `region_name=None` fails at runtime."""
    client = fake_boto3(_FakeClient(payload="{}"))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    load_aws_secrets()

    assert client.region == "ap-south-1"


def test_existing_env_wins_by_default(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    fake_boto3(_FakeClient(payload=json.dumps({"LOG_LEVEL": "DEBUG"})))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    assert load_aws_secrets() == []
    assert os.environ["LOG_LEVEL"] == "WARNING"


def test_override_flag_replaces_existing(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    fake_boto3(_FakeClient(payload=json.dumps({"LOG_LEVEL": "DEBUG"})))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    assert load_aws_secrets(override=True) == ["LOG_LEVEL"]
    assert os.environ["LOG_LEVEL"] == "DEBUG"


def test_null_values_are_skipped(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    fake_boto3(_FakeClient(payload=json.dumps({"APOLLO_API_KEY": None, "LOG_LEVEL": "INFO"})))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)
    monkeypatch.delenv("APOLLO_API_KEY", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert load_aws_secrets() == ["LOG_LEVEL"]
    assert "APOLLO_API_KEY" not in os.environ


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not json", "not valid JSON"),
        (json.dumps(["a", "b"]), "must be a JSON object"),
        (None, "no SecretString"),
    ],
)
def test_a_malformed_secret_stops_startup(
    monkeypatch: pytest.MonkeyPatch, fake_boto3, payload: str | None, message: str
) -> None:
    fake_boto3(_FakeClient(payload=payload))
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)

    with pytest.raises(SecretsLoadError, match=message):
        load_aws_secrets()


def test_fetch_failure_stops_startup(monkeypatch: pytest.MonkeyPatch, fake_boto3) -> None:
    client = fake_boto3(_FakeClient())
    from botocore.exceptions import ClientError  # the stub installed above

    client._error = ClientError("denied")
    monkeypatch.setenv(SECRETS_ID_VAR, SECRET)

    with pytest.raises(SecretsLoadError, match="could not fetch"):
        load_aws_secrets()
