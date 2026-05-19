"""Connector Service Feature Flags.

Single source of truth for the runtime kill-switches consumed by the
custom-MCP routes. Reads from env so ops can flip them per-environment
without a redeploy of code (Helm value -> ConfigMap -> env -> pod
restart on rollout is fine).
"""

import os

# When false: /catalog and /installed still work, but POST/DELETE/revalidate
# on /custom return 404 (route disabled). Default true so dev + staging
# light up; flip to false in prod values if ops wants gradual rollout.
ALLOW_CUSTOM_MCP_CONNECTORS_ENV = "ALLOW_CUSTOM_MCP_CONNECTORS"

# When true: handshake validator skips the private-IP block, allowing
# loopback/RFC1918 targets. Default false. ONLY meant for the local-dev
# script + CI; should never be set in staging/production.
ALLOW_PRIVATE_MCP_HOSTS_ENV = "ALLOW_PRIVATE_MCP_HOSTS"


def custom_mcp_enabled() -> bool:
    """Return True when /custom routes are active.

    Defaults to true so dev environments work out of the box. Set
    ``ALLOW_CUSTOM_MCP_CONNECTORS=false`` to disable. Any non-truthy
    string ("0", "false", "no", "") disables.
    """
    raw = os.getenv(ALLOW_CUSTOM_MCP_CONNECTORS_ENV, "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def allow_private_mcp_hosts() -> bool:
    """Return True when the handshake validator should skip the private-IP block.

    Default false. Local-dev + the unit/component test fixtures flip this
    on so they can target 127.0.0.1 / localhost mock servers.
    """
    raw = os.getenv(ALLOW_PRIVATE_MCP_HOSTS_ENV, "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
