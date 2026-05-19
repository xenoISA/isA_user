"""
Dev Vault — IN-PROCESS SECRET STUB.

xenoISA/isA_user#464: the real ``vault_service`` exposes
``POST /api/v1/vault/secrets`` and friends, but it requires ``user_id``
extraction plus the encryption stack to be fully bootstrapped. To land
the connector_service backend slice in a single PR we stub the secret
plane here — DO NOT USE IN PRODUCTION.

Behavior:
  * ``store_secret`` returns a deterministic ``vault_ref`` string that
    we persist in ``custom_mcp_connector.auth_secret_ref``. The actual
    bytes are held in-memory only — losing them on pod restart is
    intentional for the stub (forces a re-prompt for the secret).
  * ``revoke_secret`` is a no-op stub. The real vault would invalidate
    the secret object.

Follow-up issue tracked separately: "wire connector_service to real
vault_service before prod" — referenced in the PR body.

Toggle: ``CONNECTOR_USE_DEV_VAULT`` (default true). When false, the
caller is expected to inject a real ``VaultClient`` via the factory —
hook is in place but no production client is shipped in this PR.
"""

from __future__ import annotations

import logging
import os
import secrets
from threading import RLock
from typing import Dict, Optional

logger = logging.getLogger(__name__)


_DEV_STORE: Dict[str, str] = {}
_LOCK = RLock()


def use_dev_vault() -> bool:
    """Return True when the in-process dev_vault stub is active.

    Default true so the service runs out of the box. Flip to false once
    the real ``vault_service`` integration lands.
    """
    raw = os.getenv("CONNECTOR_USE_DEV_VAULT", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def store_secret(user_id: str, label: str, secret_value: str) -> str:
    """Store a secret and return an opaque ref to persist in the DB.

    The ref shape is ``devvault:<user_id>:<random>`` so it's obvious from
    a row dump that the row is talking to the stub vault, not the real
    one. Returns the ref even if the secret is empty (caller decides
    whether to record one).
    """
    if not secret_value:
        # Nothing to store; nothing to ref.
        return ""
    ref = f"devvault:{user_id}:{secrets.token_urlsafe(16)}"
    with _LOCK:
        _DEV_STORE[ref] = secret_value
    logger.info(
        "dev_vault: stored secret for user=%s label=%s ref=%s (in-process stub; replace before prod)",
        user_id,
        label,
        ref,
    )
    return ref


def get_secret(ref: str) -> Optional[str]:
    """Return the stored secret value, or None if it's not in the store."""
    if not ref:
        return None
    with _LOCK:
        return _DEV_STORE.get(ref)


def revoke_secret(ref: str) -> bool:
    """Remove a secret from the in-memory store. Idempotent."""
    if not ref:
        return True
    with _LOCK:
        existed = ref in _DEV_STORE
        _DEV_STORE.pop(ref, None)
    logger.info("dev_vault: revoked ref=%s (existed=%s)", ref, existed)
    return True


def _reset_for_tests() -> None:
    """Test-only: blow away the in-memory store between cases."""
    with _LOCK:
        _DEV_STORE.clear()
