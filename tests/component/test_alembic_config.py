"""L2 Component tests for Alembic configuration.

Tests that alembic.ini and env.py produce correct configuration
when combined with service arguments.
"""
import configparser
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestAlembicIni:
    """Test that alembic.ini is valid and has required fields."""

    @pytest.fixture(autouse=True)
    def load_config(self):
        self.config = configparser.ConfigParser()
        ini_path = PROJECT_ROOT / "alembic.ini"
        assert ini_path.exists(), "alembic.ini must exist at project root"
        self.config.read(str(ini_path))

    def test_has_alembic_section(self):
        assert "alembic" in self.config.sections()

    def test_script_location(self):
        assert self.config.get("alembic", "script_location") == "alembic"

    def test_sqlalchemy_url_is_placeholder(self):
        """URL should be overridden by env.py, so ini has a placeholder."""
        url = self.config.get("alembic", "sqlalchemy.url", fallback="")
        # Should be empty or a placeholder — real URL comes from env vars
        assert "production" not in url.lower()


class TestAlembicEnvModule:
    """Test that the env.py module is importable and has required functions."""

    def test_env_py_exists(self):
        env_path = PROJECT_ROOT / "alembic" / "env.py"
        assert env_path.exists(), "alembic/env.py must exist"

    def test_helpers_importable(self):
        """The helpers module should be importable from project root."""
        result = subprocess.run(
            [sys.executable, "-c", "from core.migration_helpers import get_database_url; print(get_database_url())"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env={**dict(__import__("os").environ), "PYTHONPATH": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "postgresql://" in result.stdout


class TestMigrationScriptTemplate:
    """Test that the Mako template exists and has upgrade/downgrade."""

    def test_template_exists(self):
        tmpl = PROJECT_ROOT / "alembic" / "script.py.mako"
        assert tmpl.exists()

    def test_template_has_upgrade_downgrade(self):
        tmpl = PROJECT_ROOT / "alembic" / "script.py.mako"
        content = tmpl.read_text()
        assert "def upgrade()" in content
        assert "def downgrade()" in content


class TestServiceMigrationStructure:
    """Test that the 3 representative services have proper alembic structure."""

    @pytest.mark.parametrize("service", ["account_service", "auth_service", "payment_service"])
    def test_versions_directory_exists(self, service):
        versions = PROJECT_ROOT / "microservices" / service / "alembic" / "versions"
        assert versions.is_dir(), f"{service} must have alembic/versions/"

    @pytest.mark.parametrize("service", ["account_service", "auth_service", "payment_service"])
    def test_has_initial_migration(self, service):
        versions = PROJECT_ROOT / "microservices" / service / "alembic" / "versions"
        py_files = list(versions.glob("*.py"))
        assert len(py_files) >= 1, f"{service} must have at least one migration revision"

    @pytest.mark.parametrize("service", ["account_service", "auth_service", "payment_service"])
    def test_migration_has_upgrade_downgrade(self, service):
        versions = PROJECT_ROOT / "microservices" / service / "alembic" / "versions"
        for py_file in versions.glob("*.py"):
            content = py_file.read_text()
            assert "def upgrade()" in content, f"{py_file.name} missing upgrade()"
            assert "def downgrade()" in content, f"{py_file.name} missing downgrade()"
