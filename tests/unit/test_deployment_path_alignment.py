from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DEPLOYMENT_PATH = "deployment/k8s/"
MACHINE_SPECIFIC_REPO_PATH = "/Users/xenodennis/Documents/Fun/isA_user"
ACTIVE_DEPLOYMENT_FILES = [
    REPO_ROOT / ".github" / "workflows" / "deploy.yml",
    REPO_ROOT / "scripts" / "redeploy_k8s.sh",
    REPO_ROOT / "scripts" / "init-agentic-project.sh",
    REPO_ROOT / "deployment" / "README.md",
    REPO_ROOT / "deployment" / "helm" / "deploy.sh",
    REPO_ROOT / "docs" / "guidance" / "architecture.md",
    REPO_ROOT / "docs" / "guidance" / "quickstart.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "config" / "ports.yaml",
]
EXPECTED_ACTIVE_DEPLOYMENT_PATHS = [
    "deployment/docker/Dockerfile.base",
    "deployment/docker/Dockerfile.microservice",
    "deployment/docker/build.sh",
    "deployment/helm/deploy.sh",
]


class TestDeploymentPathAlignment(unittest.TestCase):
    def test_active_deployment_files_do_not_reference_removed_k8s_path(self):
        for path in ACTIVE_DEPLOYMENT_FILES:
            file_text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                LEGACY_DEPLOYMENT_PATH,
                file_text,
                f"{path} still references the removed {LEGACY_DEPLOYMENT_PATH} path",
            )

    def test_workflow_and_redeploy_script_use_existing_active_paths(self):
        workflow_text = (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(
            encoding="utf-8"
        )
        redeploy_script_text = (
            REPO_ROOT / "scripts" / "redeploy_k8s.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("deployment/docker/Dockerfile.base", workflow_text)
        self.assertIn("deployment/docker/Dockerfile.microservice", workflow_text)
        self.assertIn("deployment/docker/build.sh", redeploy_script_text)
        self.assertIn("core/deployment_targets.py", redeploy_script_text)

        for relative_path in EXPECTED_ACTIVE_DEPLOYMENT_PATHS:
            self.assertTrue(
                (REPO_ROOT / relative_path).exists(),
                f"Expected active deployment path missing: {relative_path}",
            )

    def test_active_scripts_do_not_use_machine_specific_repo_paths(self):
        for path in (
            REPO_ROOT / "scripts" / "redeploy_k8s.sh",
            REPO_ROOT / "deployment" / "helm" / "deploy.sh",
        ):
            file_text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                MACHINE_SPECIFIC_REPO_PATH,
                file_text,
                f"{path} still uses machine-specific path {MACHINE_SPECIFIC_REPO_PATH}",
            )

    def test_staging_helm_dry_run_accepts_chart_path_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            chart_dir = temp_path / "isa-service"
            chart_dir.mkdir()
            (chart_dir / "Chart.yaml").write_text(
                "apiVersion: v2\nname: isa-service\nversion: 0.1.0\n",
                encoding="utf-8",
            )

            bin_dir = temp_path / "bin"
            bin_dir.mkdir()
            helm_log = temp_path / "helm.log"
            helm_path = bin_dir / "helm"
            helm_path.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$@\" >> \"$HELM_LOG\"\n"
                "exit 0\n",
                encoding="utf-8",
            )
            helm_path.chmod(helm_path.stat().st_mode | stat.S_IEXEC)

            env = os.environ.copy()
            env["ISA_SERVICE_CHART_PATH"] = str(chart_dir)
            env["HELM_LOG"] = str(helm_log)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", "deployment/helm/deploy.sh", "staging", "auth", "--dry-run"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stderr or result.stdout,
            )
            self.assertIn(
                "--dry-run",
                helm_log.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
