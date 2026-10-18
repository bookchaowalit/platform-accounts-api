#!/usr/bin/env python3
"""Read-only projection of the Solo Empire account matrix.

``accounts/ACCOUNT-MATRIX.yaml`` stays the canonical source that humans and AI
agents edit; this service only reshapes it into JSON for the Solo Web module.
It never reads credentials, and anonymous identities are returned as counts
only so the UI cannot link them to the public identity.

Run locally from the repository root with::

    python3 services/accounts-metadata-api/server.py

Set ``ACCOUNTS_API_MATRIX_PATH`` to use another matrix and
the ``ACCOUNTS_API_AUTH_*`` policy before exposing the service outside local development.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from service_auth import AuthError, AuthPolicy, check_read_auth, is_loopback, readiness

import yaml

from _sentry import init_sentry

init_sentry()


SERVICE_NAME = "solo-empire-accounts-api"
SCHEMA_VERSION = "solo-empire.accounts.v1"
MAX_QUERY_LENGTH = 80
MAX_FILTER_LENGTH = 40


class ApiError(Exception):
    """An expected client or service error with a safe public message."""

    def __init__(self, status: int, message: str, *, code: str = "request_error") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


@dataclass(frozen=True)
class Response:
    status: int
    payload: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository_root() -> Path:
    # <accounts>/services/accounts-metadata-api/server.py -> <accounts>
    return Path(__file__).resolve().parents[2]


def default_matrix_path() -> Path:
    configured = os.environ.get("ACCOUNTS_API_MATRIX_PATH")
    return Path(configured).expanduser() if configured else repository_root() / "accounts" / "ACCOUNT-MATRIX.yaml"


def text(value: Any, max_length: int = 200) -> str:
    return "" if value is None else str(value).strip()[:max_length]


def query_value(query: Mapping[str, list[str]], field: str, max_length: int) -> str:
    value = (query.get(field) or [""])[0].strip()
    if len(value) > max_length:
        raise ApiError(400, f"{field} is too long", code="invalid_field")
    return value


def account_row(group: dict[str, Any], item: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    row = {
        "group_id": group["id"],
        "group_kind": group["kind"],
        "platform": text(item.get("platform"), 40),
        "name": text(item.get("name"), 80),
        "purpose": text(item.get("purpose"), 200),
        "status": text(item.get("status"), 40) or "unknown",
        "face_visible": item.get("face_visible", group.get("face_visible")),
        "evidence": text(item.get("evidence"), 200) or None,
    }
    row.update(overrides)
    return row


def project_matrix(matrix: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Return (groups, account rows, anonymous aggregate) from the raw matrix."""
    groups: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for layer in matrix.get("identity_layers") or []:
        group = {
            "id": text(layer.get("id"), 60), "kind": "identity",
            "label": text(layer.get("display_name"), 80) or text(layer.get("id"), 60),
            "description": text(layer.get("purpose")), "privacy": text(layer.get("privacy"), 40) or None,
            "face_visible": layer.get("face_visible"),
        }
        groups.append(group)
        rows.extend(account_row(group, item) for item in layer.get("platforms") or [])

    for brand in matrix.get("faceless_brands") or []:
        group = {
            "id": text(brand.get("id"), 60), "kind": "brand", "label": text(brand.get("id"), 60),
            "description": text(brand.get("topic")), "privacy": "public", "face_visible": False,
        }
        groups.append(group)
        for platform in brand.get("platforms") or []:
            rows.append(account_row(group, brand, platform=text(platform, 40), name=group["id"], purpose=group["description"]))

    existing = matrix.get("existing_platform_records") or []
    if existing:
        group = {
            "id": "existing-records", "kind": "existing", "label": "Existing platform records",
            "description": "Platform use found in other documents; confirm before relying on it.",
            "privacy": None, "face_visible": None,
        }
        groups.append(group)
        rows.extend(account_row(group, item) for item in existing)

    anonymous = matrix.get("anonymous_identities") or {}
    if "aggregate" in anonymous:
        aggregate = anonymous["aggregate"]
        if (not isinstance(aggregate, dict) or
                any(type(aggregate.get(field)) is not int or aggregate[field] < 0
                    for field in ("identities", "platform_slots")) or
                not isinstance(aggregate.get("by_status"), list) or
                any(not isinstance(item, dict) or not isinstance(item.get("value"), str) or
                    type(item.get("count")) is not int or item["count"] < 0 for item in aggregate["by_status"])):
            raise ValueError("anonymous aggregate requires counts and status totals")
        anonymous_summary = {
            "isolation_required": bool(anonymous.get("isolation_required", True)),
            "identities": aggregate["identities"], "platform_slots": aggregate["platform_slots"],
            "by_status": [{"value": text(item["value"], 40) or "unknown", "count": item["count"]}
                          for item in aggregate["by_status"]],
        }
    else:
        anonymous_accounts = anonymous.get("accounts") or []
        anonymous_summary = {
            "isolation_required": bool(anonymous.get("isolation_required", True)),
            "identities": len(anonymous_accounts),
            "platform_slots": sum(len(item.get("platforms") or []) for item in anonymous_accounts),
            "by_status": counts(text(item.get("status"), 40) or "unknown" for item in anonymous_accounts),
        }
    for group in groups:
        group["account_count"] = sum(1 for row in rows if row["group_id"] == group["id"])
    return groups, rows, anonymous_summary


def counts(values: Any) -> list[dict[str, Any]]:
    return [{"value": key, "count": count} for key, count in sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))]


class MatrixStore:
    """Reload the YAML only when its modification time changes."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_matrix_path()
        self._lock = RLock()
        self._mtime: float | None = None
        self._snapshot: tuple[Any, ...] | None = None

    def snapshot(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
        with self._lock:
            mtime = self.path.stat().st_mtime
            if self._snapshot is None or mtime != self._mtime:
                source_text = self.path.read_text(encoding="utf-8")
                raw = yaml.safe_load(source_text) or {}
                if not isinstance(raw, dict):
                    raise ValueError("account matrix must be a mapping")
                groups, rows, anonymous = project_matrix(raw)
                metadata = {
                    "path": "accounts/ACCOUNT-MATRIX.yaml",
                    "revision": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                    "version": raw.get("version"),
                    "updated": text(raw.get("updated"), 20) or None,
                    "description": text(raw.get("description"), 400),
                    "status_definitions": [
                        {"value": key, "description": text(value)}
                        for key, value in (raw.get("status_definitions") or {}).items()
                    ],
                    "modified_at": datetime.fromtimestamp(mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                }
                self._snapshot = (groups, rows, anonymous, metadata)
                self._mtime = mtime
            return self._snapshot  # type: ignore[return-value]


class AccountsApi:
    """Transport-independent, read-only handler used by HTTP and tests."""

    def __init__(
        self,
        matrix_path: str | Path | None = None,
        *,
        token: str | None = None,
        environment: str | None = None,
        allowed_origins: tuple[str, ...] | None = None,
        auth_policy: AuthPolicy | None = None,
    ) -> None:
        self.store = MatrixStore(matrix_path)
        self.token = token if token is not None else os.environ.get("ACCOUNTS_API_TOKEN", "").strip()
        self.environment = (environment or os.environ.get("ACCOUNTS_API_ENV", "development")).strip().lower()
        self.auth_policy = auth_policy or AuthPolicy.from_env("ACCOUNTS_API_", "accounts-api", "accounts:read")
        configured_origins = os.environ.get("ACCOUNTS_API_CORS_ORIGINS", "http://127.0.0.1:3600,http://localhost:3600")
        self.allowed_origins = allowed_origins or tuple(item.strip() for item in configured_origins.split(",") if item.strip())

    def _check_read_auth(self, headers: Mapping[str, str]) -> None:
        try:
            check_read_auth(self.auth_policy, headers, environment=self.environment, token=self.token)
        except AuthError as exc:
            raise ApiError(exc.status, exc.message, code=exc.code) from None

    def _ready(self) -> Response:
        status, payload = readiness(self.auth_policy, self.environment, self.store)
        return Response(status, payload)

    def _overview(self, query: Mapping[str, list[str]]) -> Response:
        status = query_value(query, "status", MAX_FILTER_LENGTH)
        platform = query_value(query, "platform", MAX_FILTER_LENGTH)
        kind = query_value(query, "kind", MAX_FILTER_LENGTH)
        q = query_value(query, "q", MAX_QUERY_LENGTH).casefold()
        groups, rows, anonymous, metadata = self.store.snapshot()
        matched = [
            row for row in rows
            if (not status or row["status"] == status)
            and (not platform or row["platform"] == platform)
            and (not kind or row["group_kind"] == kind)
            and (not q or any(q in str(row[field] or "").casefold() for field in ("platform", "name", "purpose", "group_id")))
        ]
        matched_groups = {row["group_id"] for row in matched}
        return Response(200, {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "source": metadata,
            "summary": {
                "accounts_total": len(rows),
                "accounts_matched": len(matched),
                "groups": len(groups),
                "platforms": len({row["platform"] for row in rows}),
                "active": sum(1 for row in rows if row["status"] == "active"),
                "needs_attention": sum(1 for row in rows if row["status"] in {"needs-verification", "setup"}),
            },
            "signals": {
                "statuses": counts(row["status"] for row in rows),
                "platforms": counts(row["platform"] for row in rows),
                "kinds": counts(row["group_kind"] for row in rows),
            },
            "anonymous": anonymous,
            "filters": {"status": status, "platform": platform, "kind": kind, "q": q},
            "groups": [group for group in groups if group["id"] in matched_groups],
            "accounts": matched,
            "boundary": "non-secret inventory; anonymous identities are counts only",
        })

    def handle(self, method: str, target: str, *, headers: Mapping[str, str] | None = None) -> Response:
        request_headers = {str(key).lower(): str(value) for key, value in (headers or {}).items()}
        parsed = urlsplit(target)
        path = parsed.path.rstrip("/") or "/"
        try:
            if method == "OPTIONS":
                return Response(204, {})
            if method == "GET" and path == "/ready":
                return self._ready()
            if method == "GET" and path == "/health":
                return Response(200, {"status": "ok", "service": SERVICE_NAME, "schema_version": SCHEMA_VERSION, "timestamp": utc_now()})
            if path == "/api/v1/accounts":
                self._check_read_auth(request_headers)
                if method != "GET":
                    raise ApiError(405, "account inventory is read-only", code="method_not_allowed")
                return self._overview(parse_qs(parsed.query))
            raise ApiError(404, "route not found", code="not_found")
        except ApiError as exc:
            return Response(exc.status, {"error": {"code": exc.code, "message": exc.message}})
        except (OSError, ValueError, TypeError, yaml.YAMLError):
            return Response(503, {"error": {"code": "matrix_unavailable", "message": "Account matrix could not be read"}})
        except Exception:
            if os.environ.get("SENTRY_DSN", "").strip():  # see _sentry.py
                import sentry_sdk

                sentry_sdk.capture_exception()
            return Response(500, {"error": {"code": "internal_error", "message": "Accounts service could not complete the request"}})


class AccountsRequestHandler(BaseHTTPRequestHandler):
    api = AccountsApi()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _dispatch(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin not in self.api.allowed_origins:
            self._write(Response(403, {"error": {"code": "origin_not_allowed", "message": "origin is not allowed"}}), origin=None)
            return
        self._write(self.api.handle(self.command, self.path, headers=dict(self.headers.items())), origin=origin)

    def _write(self, response: Response, *, origin: str | None) -> None:
        encoded = b"" if response.status == HTTPStatus.NO_CONTENT else json.dumps(response.payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        if origin and origin in self.api.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        if self.command == "OPTIONS":
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Accept, Authorization")
        self.end_headers()
        if response.status != HTTPStatus.NO_CONTENT:
            self.wfile.write(encoded)

    do_GET = _dispatch
    do_OPTIONS = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch
    do_DELETE = _dispatch


def main() -> None:
    parser = argparse.ArgumentParser(description="Solo Empire account matrix API")
    parser.add_argument("--host", default=os.environ.get("ACCOUNTS_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ACCOUNTS_API_PORT", os.environ.get("PORT", "3470"))))
    parser.add_argument("--matrix", default=None, help="account matrix YAML; defaults to ACCOUNTS_API_MATRIX_PATH or accounts/ACCOUNT-MATRIX.yaml")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.matrix:
        AccountsRequestHandler.api = AccountsApi(args.matrix)
    if not is_loopback(args.host):
        AccountsRequestHandler.api.environment = "production"
        if not AccountsRequestHandler.api.auth_policy.ready:
            parser.error("a non-loopback --host requires valid ACCOUNTS_API_AUTH_* configuration")
    server = ThreadingHTTPServer((args.host, args.port), AccountsRequestHandler)
    print(f"{SERVICE_NAME} running on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
