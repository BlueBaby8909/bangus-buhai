"""Offline protection of the explicit database/test-environment boundary."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.database import config
from backend.database import local


class DatabaseConfigurationTests(unittest.TestCase):
    def test_no_implicit_database_or_prototype_configuration(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            with patch.object(config, "LOCAL_ENV", Path(folder) / "missing.env"):
                with self.assertRaisesRegex(RuntimeError, "Missing BB_DATABASE_URL"):
                    config.database_url()

    def test_test_target_must_be_dedicated_postgresql_database(self):
        for url in ("sqlite:///prototype.db", "postgresql+psycopg://localhost/bangus_buhai_rebuild",
                    "postgresql+psycopg://localhost/production", "postgresql+psycopg://localhost/"):
            with self.subTest(url=url), patch.dict(os.environ, {"BB_TEST_DATABASE_URL": url}):
                with self.assertRaises(RuntimeError):
                    config.database_url(test=True)

    def test_environment_overrides_only_rebuild_local_file(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / ".env"
            local.write_text("BB_DATABASE_URL=postgresql+psycopg://localhost/file_database\n", encoding="utf-8")
            with patch.object(config, "LOCAL_ENV", local), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(config.database_url().database, "file_database")
                with patch.dict(os.environ, {"BB_DATABASE_URL": "postgresql+psycopg://localhost/environment_database"}):
                    self.assertEqual(config.database_url().database, "environment_database")

    def test_local_setup_preserves_generated_secret_after_docker_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / ".env"
            with patch.object(local, "LOCAL_ENV", destination), patch.object(local.sys, "argv", ["local", "up"]):
                with patch.object(local.subprocess, "call", return_value=1):
                    with self.assertRaises(SystemExit) as error:
                        local.main()
                    self.assertEqual(error.exception.code, 1)
                    original = destination.read_bytes()
                    self.assertIn(b"BB_DATABASE_URL=postgresql+psycopg://", original)
                    self.assertIn(b"bangus_buhai_rebuild_test", original)
                    with self.assertRaises(SystemExit):
                        local.main()
                    self.assertEqual(destination.read_bytes(), original)

    def test_local_stop_does_not_create_credentials_or_invoke_docker(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / ".env"
            with patch.object(local, "LOCAL_ENV", destination), patch.object(local.sys, "argv", ["local", "stop"]):
                with patch.object(local.subprocess, "call") as docker:
                    with self.assertRaises(SystemExit):
                        local.main()
                    self.assertFalse(destination.exists())
                    docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
