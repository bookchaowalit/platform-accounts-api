#!/usr/bin/env python3
"""Focused offline tests for the account matrix projection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from service_auth import AuthPolicy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import AccountsApi  # noqa: E402

MATRIX = """
version: 1
updated: '2026-08-02'
description: Fixture matrix
status_definitions:
  active: Configured
  planned: Intended
identity_layers:
  - id: public-personal
    display_name: Public
    face_visible: true
    privacy: public
    purpose: Professional identity
    platforms:
      - {platform: github, purpose: personal, name: book, status: active, evidence: accounts/github}
      - {platform: linkedin, purpose: personal, name: book, status: needs-verification}
faceless_brands:
  - {id: artbybook, platforms: [instagram, tiktok], status: planned, topic: Art guides}
existing_platform_records:
  - {platform: facebook, name: sme-page, purpose: business, face_visible: false, status: needs-verification, evidence: dashboard/TOOLS-REGISTRY.md}
anonymous_identities:
  isolation_required: true
  accounts:
    - {id: secret-handle, platforms: [x, reddit], status: planned, purpose: Private venting}
"""


class AccountsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "matrix.yaml"
        self.path.write_text(MATRIX, encoding="utf-8")
        self.api = AccountsApi(
            self.path,
            token="",
            environment="development",
            allowed_origins=("http://127.0.0.1:3600",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def get(self, target: str, **kwargs):
        return self.api.handle("GET", target, **kwargs)

    def test_scoped_production_auth_and_safe_errors(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        policy = AuthPolicy(
            "https://solo.example",
            "accounts-api",
            public,
            frozenset({"fixture-owner"}),
            "accounts:read",
        )
        api = AccountsApi(self.path, environment="production", auth_policy=policy)
        now = int(time.time())
        claims = {
            "iss": "https://solo.example",
            "aud": "accounts-api",
            "sub": "fixture-owner",
            "tenant_id": "owner",
            "scope": "accounts:read",
            "iat": now,
            "nbf": now,
            "exp": now + 120,
            "jti": "fixture-request",
        }

        def headers(changes=None):
            return {
                "Authorization": "Bearer "
                + jwt.encode({**claims, **(changes or {})}, key, algorithm="RS256")
            }

        self.assertEqual(api.handle("GET", "/health").status, 200)
        self.assertEqual(api.handle("GET", "/ready").status, 200)
        self.assertEqual(api.handle("GET", "/api/v1/accounts").status, 401)
        response = api.handle("GET", "/api/v1/accounts", headers=headers())
        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.payload["source"]["revision"]), 64)
        for changes, expected in (
            ({"scope": "other:read"}, 403),
            ({"tenant_id": "other"}, 403),
            ({"sub": "other-owner"}, 403),
            ({"iss": "https://other.example"}, 401),
            ({"aud": "other-api"}, 401),
            ({"exp": now - 300}, 401),
            ({"nbf": now + 300}, 401),
        ):
            with self.subTest(changes=changes):
                denied = api.handle("GET", "/api/v1/accounts", headers=headers(changes))
                self.assertEqual(denied.status, expected)
                self.assertEqual(set(denied.payload), {"error"})
                self.assertNotIn("Bearer", json.dumps(denied.payload))
        self.assertEqual(
            api.handle(
                "GET",
                "/api/v1/accounts",
                headers={"Authorization": "Bearer " + "x" * 9000},
            ).status,
            401,
        )

    def test_static_token_is_never_production_authorization(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = AccountsApi(
                self.path, token="development-only", environment="production"
            )
        self.assertEqual(
            api.handle(
                "GET",
                "/api/v1/accounts",
                headers={"Authorization": "Bearer development-only"},
            ).status,
            503,
        )
        self.assertEqual(api.handle("GET", "/health").status, 200)
        self.assertEqual(api.handle("GET", "/ready").payload["auth"], "disabled")

    def test_readiness_and_remote_bind_fail_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = AccountsApi(self.path, environment="development")
        self.assertEqual(api.handle("GET", "/ready").payload["auth"], "development")
        self.assertEqual(api.handle("GET", "/ready").status, 503)
        self.path.unlink()
        self.assertEqual(api.handle("GET", "/ready").payload["source"], "unavailable")
        self.assertEqual(api.handle("GET", "/health").status, 200)
        env = {
            **os.environ,
            "ACCOUNTS_API_TOKEN": "legacy-token",
            "ACCOUNTS_API_ENV": "development",
        }
        for suffix in ("AUTH_ISSUER", "AUTH_PUBLIC_KEY", "AUTH_SUBJECTS"):
            env.pop("ACCOUNTS_API_" + suffix, None)
        result = subprocess.run(
            [sys.executable, str(ROOT / "server.py"), "--host", "0.0.0.0"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ACCOUNTS_API_AUTH_*", result.stderr)

    def test_overview_flattens_every_section(self) -> None:
        response = self.get("/api/v1/accounts")
        self.assertEqual(response.status, 200)
        payload = response.payload
        self.assertEqual(payload["schema_version"], "solo-empire.accounts.v1")
        self.assertEqual(payload["summary"]["accounts_total"], 5)
        self.assertEqual(payload["summary"]["active"], 1)
        self.assertEqual(payload["summary"]["needs_attention"], 2)
        brand_rows = [
            row for row in payload["accounts"] if row["group_kind"] == "brand"
        ]
        self.assertEqual(
            {row["platform"] for row in brand_rows}, {"instagram", "tiktok"}
        )
        self.assertEqual(
            payload["source"]["status_definitions"][0],
            {"value": "active", "description": "Configured"},
        )

    def test_anonymous_identities_are_counts_only(self) -> None:
        payload = self.get("/api/v1/accounts").payload
        self.assertEqual(
            payload["anonymous"],
            {
                "isolation_required": True,
                "identities": 1,
                "platform_slots": 2,
                "by_status": [{"value": "planned", "count": 1}],
            },
        )
        encoded = json.dumps(payload)
        self.assertNotIn("secret-handle", encoded)
        self.assertNotIn("Private venting", encoded)

    def test_anonymous_aggregate_preserves_v1_output_without_identity_details(
        self,
    ) -> None:
        before = self.get("/api/v1/accounts").payload
        matrix = yaml.safe_load(MATRIX)
        matrix["anonymous_identities"] = {
            "isolation_required": True,
            "aggregate": {
                "identities": 1,
                "platform_slots": 2,
                "by_status": [
                    {
                        "value": "planned",
                        "count": 1,
                        "private_name": "AGGREGATE_PRIVATE_MARKER",
                    }
                ],
                "private_id": "AGGREGATE_PRIVATE_MARKER",
            },
        }
        self.path.write_text(yaml.safe_dump(matrix), encoding="utf-8")
        response = AccountsApi(self.path, token="", environment="development").handle(
            "GET", "/api/v1/accounts"
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(response.payload["schema_version"], "solo-empire.accounts.v1")
        for field in ("accounts", "groups", "summary", "signals", "anonymous"):
            self.assertEqual(response.payload[field], before[field], field)
        self.assertNotIn("AGGREGATE_PRIVATE_MARKER", json.dumps(response.payload))

    def test_anonymous_aggregate_rejects_non_numeric_or_malformed_counts(self) -> None:
        for aggregate in (
            {
                "identities": "AGGREGATE_PRIVATE_MARKER",
                "platform_slots": 2,
                "by_status": [],
            },
            {"identities": True, "platform_slots": 2, "by_status": []},
            {"identities": 1, "platform_slots": -1, "by_status": []},
            {
                "identities": 1,
                "platform_slots": 2,
                "by_status": [
                    {"value": "planned", "count": "AGGREGATE_PRIVATE_MARKER"}
                ],
            },
            {
                "identities": 1,
                "platform_slots": 2,
                "by_status": {"private": "AGGREGATE_PRIVATE_MARKER"},
            },
        ):
            with self.subTest(aggregate=aggregate):
                matrix = yaml.safe_load(MATRIX)
                matrix["anonymous_identities"] = {"aggregate": aggregate}
                self.path.write_text(yaml.safe_dump(matrix), encoding="utf-8")
                response = AccountsApi(
                    self.path, token="", environment="development"
                ).handle("GET", "/api/v1/accounts")
                self.assertEqual(response.status, 503)
                self.assertEqual(
                    response.payload["error"]["code"], "matrix_unavailable"
                )
                self.assertNotIn(
                    "AGGREGATE_PRIVATE_MARKER", json.dumps(response.payload)
                )

    def test_filters(self) -> None:
        payload = self.get(
            "/api/v1/accounts?status=needs-verification&kind=existing"
        ).payload
        self.assertEqual([row["name"] for row in payload["accounts"]], ["sme-page"])
        self.assertEqual(
            [group["id"] for group in payload["groups"]], ["existing-records"]
        )
        payload = self.get("/api/v1/accounts?q=ART").payload
        self.assertEqual(payload["summary"]["accounts_matched"], 2)
        self.assertEqual(self.get("/api/v1/accounts?q=" + "x" * 81).status, 400)

    def test_read_only_and_routes(self) -> None:
        self.assertEqual(self.api.handle("POST", "/api/v1/accounts").status, 405)
        self.assertEqual(self.get("/api/v1/other").status, 404)
        self.assertEqual(self.get("/health").payload["status"], "ok")

    def test_token_and_production_gate(self) -> None:
        guarded = AccountsApi(self.path, token="t0ken", environment="development")
        self.assertEqual(guarded.handle("GET", "/api/v1/accounts").status, 401)
        self.assertEqual(
            guarded.handle(
                "GET", "/api/v1/accounts", headers={"Authorization": "Bearer t0ken"}
            ).status,
            200,
        )
        production = AccountsApi(self.path, token="", environment="production")
        self.assertEqual(production.handle("GET", "/api/v1/accounts").status, 503)

    def test_unreadable_matrix_is_503(self) -> None:
        self.path.write_text("- not a mapping\n", encoding="utf-8")
        response = self.get("/api/v1/accounts")
        self.assertEqual(response.status, 503)
        self.assertEqual(response.payload["error"]["code"], "matrix_unavailable")

    def test_real_matrix_projects(self) -> None:
        real = Path(
            os.environ.get("ACCOUNTS_API_MATRIX_PATH")
            or Path(__file__).resolve().parents[3] / "accounts" / "ACCOUNT-MATRIX.yaml"
        )
        if not real.is_file():
            self.skipTest(f"account matrix not present at {real}")
        response = AccountsApi(real, token="", environment="development").handle(
            "GET", "/api/v1/accounts"
        )
        self.assertEqual(response.status, 200)
        self.assertGreater(response.payload["summary"]["accounts_total"], 0)


if __name__ == "__main__":
    unittest.main()
