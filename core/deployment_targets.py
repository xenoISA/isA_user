"""Canonical deploy target resolution for isA_user microservices."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PORTS_CONFIG_PATH = REPO_ROOT / "config" / "ports.yaml"
MICROSERVICES_DIR = REPO_ROOT / "microservices"


@dataclass(frozen=True)
class DeployTarget:
    service_dir: str
    short_name: str
    image_name: str
    k8s_service_name: str
    release_name: str
    deployment_name: str
    container_name: str
    port: int


def _load_microservice_config(config_path: Path = PORTS_CONFIG_PATH) -> dict[str, dict]:
    microservices: dict[str, dict] = {}
    current_service: str | None = None
    in_microservices = False

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 0:
            in_microservices = stripped == "microservices:"
            current_service = None
            continue

        if not in_microservices:
            continue

        if indent == 2 and stripped.endswith(":"):
            current_service = stripped[:-1]
            microservices[current_service] = {}
            continue

        if current_service is None or indent < 4 or ":" not in stripped:
            continue

        key, _, raw_value = stripped.partition(":")
        value = raw_value.strip().strip('"').strip("'")

        if key == "port":
            microservices[current_service]["port"] = int(value)
        elif key == "k8s_service":
            microservices[current_service]["k8s_service"] = value

    return microservices


def _build_short_name_index(
    microservices: dict[str, dict],
) -> dict[str, str]:
    short_name_index: dict[str, str] = {}

    for service_dir, details in microservices.items():
        short_name = details.get("k8s_service")
        if not short_name:
            raise ValueError(f"Missing k8s_service mapping for {service_dir}")
        if short_name in short_name_index and short_name_index[short_name] != service_dir:
            raise ValueError(
                f"Duplicate k8s_service mapping '{short_name}' in config/ports.yaml"
            )
        short_name_index[short_name] = service_dir

    return short_name_index


def list_service_directories(
    microservices_dir: Path = MICROSERVICES_DIR,
    config_path: Path = PORTS_CONFIG_PATH,
) -> list[str]:
    configured_services = _load_microservice_config(config_path)
    configured_service_dirs = set(configured_services)

    return sorted(
        path.name
        for path in microservices_dir.iterdir()
        if path.is_dir() and path.name.endswith("_service")
        and path.name in configured_service_dirs
    )


def resolve_deploy_target(
    service: str,
    config_path: Path = PORTS_CONFIG_PATH,
) -> DeployTarget:
    raw_service = service.strip()
    if not raw_service:
        raise ValueError("Service name cannot be empty")

    microservices = _load_microservice_config(config_path)
    short_name_index = _build_short_name_index(microservices)

    if raw_service in microservices:
        service_dir = raw_service
    elif raw_service in short_name_index:
        service_dir = short_name_index[raw_service]
    elif raw_service.endswith("_service"):
        raise ValueError(f"Unknown service '{raw_service}'")
    else:
        raise ValueError(
            f"Unknown service '{raw_service}'. Expected a configured *_service directory "
            "name or short kubernetes service name."
        )

    service_config = microservices[service_dir]
    short_name = service_config["k8s_service"]
    release_name = f"user-{short_name}-service"

    return DeployTarget(
        service_dir=service_dir,
        short_name=short_name,
        image_name=short_name,
        k8s_service_name=short_name,
        release_name=release_name,
        deployment_name=release_name,
        container_name=release_name,
        port=int(service_config["port"]),
    )


def normalize_requested_services(
    services: str,
    config_path: Path = PORTS_CONFIG_PATH,
) -> list[str]:
    requested_services = [item.strip() for item in services.split(",") if item.strip()]
    if not requested_services:
        raise ValueError("No services were provided")

    normalized: list[str] = []
    seen: set[str] = set()
    for service in requested_services:
        target = resolve_deploy_target(service, config_path=config_path)
        if target.service_dir not in seen:
            normalized.append(target.service_dir)
            seen.add(target.service_dir)

    return normalized


def _format_env(target: DeployTarget) -> str:
    env_values = {
        "TARGET_SERVICE_DIR": target.service_dir,
        "TARGET_SHORT_NAME": target.short_name,
        "TARGET_IMAGE_NAME": target.image_name,
        "TARGET_K8S_SERVICE_NAME": target.k8s_service_name,
        "TARGET_RELEASE_NAME": target.release_name,
        "TARGET_DEPLOYMENT_NAME": target.deployment_name,
        "TARGET_CONTAINER_NAME": target.container_name,
        "TARGET_SERVICE_PORT": str(target.port),
    }
    return "\n".join(f"{key}={value}" for key, value in env_values.items())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve canonical deploy targets for isA_user microservices."
    )
    parser.add_argument(
        "service",
        nargs="?",
        help="Service directory (auth_service) or short name (auth).",
    )
    parser.add_argument(
        "--normalize-list",
        dest="normalize_list",
        help="Normalize a comma-separated service list into *_service directory names.",
    )
    parser.add_argument(
        "--list-service-dirs",
        action="store_true",
        help="List discovered *_service directories after validating config mappings.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "env", "csv"),
        default="json",
        help="Output format for the selected operation.",
    )
    args = parser.parse_args()

    selected_operations = sum(
        bool(option)
        for option in (args.service, args.normalize_list, args.list_service_dirs)
    )
    if selected_operations != 1:
        parser.error("Provide exactly one of: SERVICE, --normalize-list, --list-service-dirs")

    if args.list_service_dirs:
        service_dirs = list_service_directories()
        if args.format == "csv":
            print(",".join(service_dirs))
        else:
            print(json.dumps(service_dirs))
        return 0

    if args.normalize_list:
        service_dirs = normalize_requested_services(args.normalize_list)
        if args.format == "csv":
            print(",".join(service_dirs))
        else:
            print(json.dumps(service_dirs))
        return 0

    target = resolve_deploy_target(args.service)
    if args.format == "env":
        print(_format_env(target))
    else:
        print(json.dumps(asdict(target)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
