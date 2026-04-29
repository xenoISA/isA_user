from pathlib import Path
import unittest

from core.deployment_targets import (
    build_k8s_service_fqdn,
    get_kubernetes_namespace,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_NAMESPACE = "isa-cloud-production"
CANONICAL_PRODUCTION_NAMESPACE = "isa-cloud-prod"
ACTIVE_NAMESPACE_FILES = [
    REPO_ROOT / "config" / "ports.yaml",
    REPO_ROOT / ".github" / "workflows" / "deploy.yml",
    REPO_ROOT / "deployment" / "helm" / "deploy.sh",
    REPO_ROOT / "deployment" / "helm" / "values-production.yaml",
    REPO_ROOT / "deployment" / "environments" / "production.env",
    REPO_ROOT / "README.md",
]


class TestProductionNamespaceConfig(unittest.TestCase):
    def test_kubernetes_namespaces_come_from_ports_config(self):
        self.assertEqual(get_kubernetes_namespace("staging"), "isa-cloud-staging")
        self.assertEqual(
            get_kubernetes_namespace("production"),
            CANONICAL_PRODUCTION_NAMESPACE,
        )

    def test_production_service_fqdns_use_canonical_namespace(self):
        self.assertEqual(
            build_k8s_service_fqdn("consul-server", "production"),
            f"consul-server.{CANONICAL_PRODUCTION_NAMESPACE}.svc.cluster.local",
        )
        self.assertEqual(
            build_k8s_service_fqdn("nats", "production"),
            f"nats.{CANONICAL_PRODUCTION_NAMESPACE}.svc.cluster.local",
        )

    def test_active_production_deploy_files_do_not_use_legacy_namespace(self):
        for path in ACTIVE_NAMESPACE_FILES:
            file_text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                LEGACY_NAMESPACE,
                file_text,
                f"{path} still uses {LEGACY_NAMESPACE}",
            )

    def test_workflow_and_helm_deploy_script_resolve_namespaces_from_config(self):
        workflow_text = (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(
            encoding="utf-8"
        )
        deploy_script_text = (
            REPO_ROOT / "deployment" / "helm" / "deploy.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "python core/deployment_targets.py --namespace staging",
            workflow_text,
        )
        self.assertIn(
            "python core/deployment_targets.py --namespace production",
            workflow_text,
        )
        self.assertIn(
            'NAMESPACE="$(python3 core/deployment_targets.py --namespace production)"',
            deploy_script_text,
        )
