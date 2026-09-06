"""Load configuration from AWS Secrets Manager into the process environment.

App Runner keeps every production setting in one Secrets Manager entry holding a flat JSON
object of ``ENV_VAR -> value``. Pointing ``AWS_SECRETS_ID`` at that secret is what turns this
module on; without it nothing here runs and the app reads its local ``.env`` exactly as in
development.

Values land in ``os.environ`` rather than in :class:`~app.core.config.Settings` directly, so
``Settings`` stays a plain pydantic-settings model with no cloud dependency and no second code
path to keep in sync.
"""

from __future__ import annotations

import json
import os

import structlog

log = structlog.get_logger()

#: Env var naming the secret (name or full ARN) to load. Unset -> no-op.
SECRETS_ID_VAR = "AWS_SECRETS_ID"


class SecretsLoadError(RuntimeError):
    """Raised when a requested secret cannot be fetched or parsed."""


def _resolve_region(secret_id: str) -> str | None:
    """Pick the region for the Secrets Manager client.

    boto3 does *not* infer a region from an ARN passed as ``SecretId``, and whether the runtime
    exports ``AWS_REGION`` into the container is not worth depending on, so a full ARN has its
    region read straight out of it. A bare secret name falls back to the standard env vars, then
    to ``None`` so boto3's own config chain decides.

    ARN shape: ``arn:aws:secretsmanager:<region>:<account>:secret:<name>``.
    """
    if secret_id.startswith("arn:"):
        parts = secret_id.split(":")
        if len(parts) > 3 and parts[3]:
            return parts[3]
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")


def load_aws_secrets(*, override: bool = False) -> list[str]:
    """Merge the JSON secret named by ``AWS_SECRETS_ID`` into ``os.environ``.

    Returns the env var names that were set, so callers can log keys and never values. Returns
    an empty list when ``AWS_SECRETS_ID`` is unset, which is every local run and the test suite.

    Existing environment variables win by default: App Runner's own ``RuntimeEnvironmentVariables``
    and anything an operator exports are deliberate per-deployment overrides of the stored value.
    Pass ``override=True`` to invert that.

    Raises:
        SecretsLoadError: the secret was requested but could not be fetched, decoded or parsed.
            Opting in makes the secret load-bearing, so this must stop startup rather than leave
            the service running on half a configuration.
    """
    secret_id = os.environ.get(SECRETS_ID_VAR, "").strip()
    if not secret_id:
        return []

    # Imported lazily so boto3 is only needed where secrets are actually used; local runs and
    # tests never pay the import cost.
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise SecretsLoadError(f"{SECRETS_ID_VAR} is set but boto3 is not installed") from exc

    client = boto3.client("secretsmanager", region_name=_resolve_region(secret_id))

    try:
        response = client.get_secret_value(SecretId=secret_id)
    except (BotoCoreError, ClientError) as exc:
        raise SecretsLoadError(f"could not fetch secret {secret_id!r}: {exc}") from exc

    raw = response.get("SecretString")
    if raw is None:
        raise SecretsLoadError(f"secret {secret_id!r} has no SecretString")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretsLoadError(f"secret {secret_id!r} is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SecretsLoadError(
            f"secret {secret_id!r} must be a JSON object, got {type(payload).__name__}"
        )

    applied: list[str] = []
    for key, value in payload.items():
        if value is None:
            continue
        if not override and key in os.environ:
            continue
        os.environ[key] = str(value)
        applied.append(key)

    # Keys only. Values are secrets and must never reach the logs.
    log.info("aws_secrets_loaded", secret_id=secret_id, keys=sorted(applied))
    return applied
