"""Sentry stays off without SENTRY_DSN; with it, errors only and no PII."""

from __future__ import annotations

import importlib
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import _sentry  # noqa: E402


class SentryTests(unittest.TestCase):
    def test_no_dsn_is_a_noop(self):
        calls = []
        fake = type("Fake", (), {"init": lambda **kw: calls.append(kw)})
        env = {k: v for k, v in os.environ.items() if k != "SENTRY_DSN"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch.dict(sys.modules, {"sentry_sdk": fake}),
        ):
            _sentry.init_sentry()
        self.assertEqual(calls, [])

    def test_dsn_initialises_errors_only_without_pii(self):
        calls, tags = [], {}

        class Fake:
            @staticmethod
            def init(**kw):
                calls.append(kw)

            @staticmethod
            def set_tag(key, value):
                tags[key] = value

        env = {k: v for k, v in os.environ.items() if k != "SENTRY_ENVIRONMENT"}
        env.update(
            SENTRY_DSN="https://public@o0.ingest.sentry.io/0",
            RAILWAY_SERVICE_NAME="accounts-metadata-api",
        )
        err = io.StringIO()
        with (
            patch.dict(os.environ, env, clear=True),
            patch.dict(sys.modules, {"sentry_sdk": Fake}),
        ):
            with redirect_stderr(err):
                _sentry.init_sentry()
        self.assertEqual(calls[0]["environment"], "production")
        self.assertEqual(calls[0]["traces_sample_rate"], 0.0)
        self.assertIs(calls[0]["send_default_pii"], False)
        self.assertEqual(tags, {"service": "accounts-metadata-api"})
        self.assertIn("sentry: enabled for accounts-metadata-api", err.getvalue())

    def test_real_sdk_installed(self):
        try:
            module = importlib.import_module("sentry_sdk")
        except ImportError:
            self.skipTest("sentry_sdk not installed")
        self.assertTrue(module)


if __name__ == "__main__":
    unittest.main()
