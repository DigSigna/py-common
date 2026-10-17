# py-common

Shared Python infrastructure for DigSigna's Python microservices (`certificate-service`, `signing-service`, and any future one). Extracted from `certificate-service` — at extraction time, every module here was byte-for-byte identical in both `certificate-service` and `signing-service` except for two one-line, service-name-specific differences (now parameters instead of hardcoded strings).

This is the Python-side sibling of a future `digsigna-go-common` equivalent for `hsm-service` (Go) and the upcoming Go services (`audit-service`, `gateway-service`) — the two are not meant to share code, only the same conceptual contracts (JWT claims shape, `audit_logs`/`idempotency_keys` schema).

## What's in here

- **`py_common.core`** — `UnifiedLogger`/`get_logger` (structured JSON logging) and request-context contextvars (correlation ID, request ID, actor, etc.).
- **`py_common.errors`** — the generic `DomainError` base (`to_dict`, stable `code`/`http_status`) plus the error subclasses shared across services (`ValidationError`, `NotFoundError`, `AuthorizationError`, `DuplicateRequestError`, `HsmError`/`AuditError` families, etc.). Each consuming service keeps its own domain-specific subclasses (e.g. `CAError`, `SigningPinError`) importing `DomainError` from here.
- **`py_common.auth`** — `KeyManagerAdapter`/`JWTValidatorAdapter` (JWT/JWKS validation), `IdentityContext`, `AuthMiddleware`, `TokenCache` (Redis-backed), and `permissions.require_admin`/`get_identity_context`.
- **`py_common.idempotency`** — `claim_idempotency_key`/`finish_idempotency_claim` plus the `IdempotencyRepository` port and its SQLAlchemy adapter, over the shared `idempotency_keys` table.
- **`py_common.audit`** — the hybrid audit pipeline: `AuditWorker` (async queue), `new_audit_recorder` (strategy factory), `HybridProcessor` (HTTP-primary/DB-fallback circuit breaker), `HttpAuditTransporter`, and the SQLAlchemy adapter over the shared `audit_logs` table.
- **`py_common.middleware`** — `RequestContextMiddleware`, `LoggingMiddleware`, `ErrorHandlingMiddleware`.

## Installing in a consumer

Distributed as a git dependency pinned to a tag, not published to PyPI:

```
# requirements/base.txt
git+https://x-access-token:${DIGSIGNA_COMMON_TOKEN}@github.com/DigSigna/py-common.git@v0.1.0
```

`DIGSIGNA_COMMON_TOKEN` (a fine-grained GitHub PAT with read access to this repo) needs to be set as a CI secret in every consuming repo — `actions/checkout`'s default token doesn't reach other private repos in the org.

## Versioning

Manual semver bump in `pyproject.toml`'s `version`, tagged `vX.Y.Z` on `main`. Consumers pin an exact tag and upgrade deliberately — never `@main`.

## Deliberate behavior changes from the original per-service copies

- `UnifiedLogger` no longer calls `get_settings()` from the consuming app — it reads `ENVIRONMENT` directly from `os.environ` (same effective value in every real deployment: both original services' `config.yaml` set `environment: "development"`, identical to the Pydantic `Field` default, so nothing actually relied on YAML-only overrides).
- `LoggingMiddleware` and `ErrorHandlingMiddleware` now take `service_name` as a constructor argument. In both original repos, `LoggingMiddleware` hardcoded `get_logger("api-gateway")` at module level with a comment claiming it would be overridden per service — it never was, so every request log line from both `certificate-service` and `signing-service` was mislabeled `"service": "api-gateway"`. This is now impossible by construction.
- `HttpAuditTransporter` and `new_audit_recorder` take `service_name` explicitly instead of a hardcoded `User-Agent` string (the one line that actually differed between the two original copies).
- `AuthMiddleware` takes an optional `exempt_paths` constructor argument (defaulting to the original hardcoded `{"/api/v1/health", "/docs", "/redoc", "/openapi.json"}`), in case a future consumer's health-check path differs.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -v --cov=py_common
.venv/bin/black --check src tests
.venv/bin/flake8 src tests
.venv/bin/bandit -r src
```
