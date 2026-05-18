"""
Artifact Repository — Postgres data-access layer.

Tables (schema ``artifact``):
  - artifact.artifacts
  - artifact.artifact_versions
  - artifact.artifact_shares  (declared in migration; not exercised in Phase 1)

We follow the pattern in ``document_repository.py`` — use ``AsyncPostgresClient``
from ``isa_common`` and pull host/port from ``ConfigManager``. Protobuf
``Struct/ListValue`` returns from the gRPC postgres service are normalised back
into native Python via ``_to_native``.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.protobuf.json_format import MessageToDict  # type: ignore
from google.protobuf.struct_pb2 import ListValue, Struct  # type: ignore
from isa_common import AsyncPostgresClient

from core.config_manager import ConfigManager
from core.postgres_client import compute_pool_size as _pg_compute_pool

from .models import (
    Artifact,
    ArtifactMCPGrant,
    ArtifactRuntimeUsage,
    ArtifactScope,
    ArtifactShare,
    ArtifactShareVisibility,
    ArtifactVersion,
    MCPGrantDecision,
    MCPGrantScope,
)

logger = logging.getLogger(__name__)


def _pg_max_pool() -> int:
    return _pg_compute_pool()


def _pg_min_pool() -> int:
    return 2 if _pg_max_pool() >= 4 else 1


def _to_native(value: Any) -> Any:
    if isinstance(value, (ListValue, Struct)):
        return MessageToDict(value, preserving_proto_field_name=True)
    return value


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _row_to_artifact(row: dict) -> Artifact:
    cleaned = dict(row)
    for k in ("metadata",):
        if k in cleaned:
            cleaned[k] = _to_native(cleaned[k])
    return Artifact.model_validate(cleaned)


def _row_to_version(row: dict) -> ArtifactVersion:
    cleaned = dict(row)
    for k in ("a2ui_state_json",):
        if k in cleaned and cleaned[k] is not None:
            cleaned[k] = _to_native(cleaned[k])
    return ArtifactVersion.model_validate(cleaned)


class ArtifactRepository:
    """Postgres repository for artifacts and their versions."""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("artifact_service")

        host, port = config.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )
        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="artifact_service",
            min_pool_size=_pg_min_pool(),
            max_pool_size=_pg_max_pool(),
        )

        self.schema = "artifact"
        self.artifacts_table = "artifacts"
        self.versions_table = "artifact_versions"

    # ==================== Artifact CRUD ====================

    async def create_artifact(self, artifact: Artifact) -> Artifact:
        data = {
            "id": artifact.id,
            "owner_user_id": artifact.owner_user_id,
            "owner_org_id": artifact.owner_org_id or "",
            "title": artifact.title,
            "content_type": artifact.content_type,
            "current_version_id": artifact.current_version_id or "",
            "source_session_id": artifact.source_session_id or "",
            "source_message_id": artifact.source_message_id or "",
            "parent_artifact_id": artifact.parent_artifact_id or "",
            "visibility": artifact.visibility.value,
            "ai_runtime_enabled": artifact.ai_runtime_enabled,
            "storage_scope": artifact.storage_scope.value,
            "metadata": artifact.metadata or {},
            "deleted_at": None,
            "created_at": _now_naive(),
            "updated_at": _now_naive(),
        }
        async with self.db:
            await self.db.insert_into(self.artifacts_table, [data], schema=self.schema)
        fetched = await self.get_artifact(artifact.id)
        if fetched is None:  # pragma: no cover - defensive
            raise RuntimeError(f"insert succeeded but artifact {artifact.id} not visible")
        return fetched

    async def get_artifact(self, artifact_id: str, include_deleted: bool = False) -> Optional[Artifact]:
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.artifacts_table}
                WHERE id = $1
            """
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            async with self.db:
                row = await self.db.query_row(query, [artifact_id], schema=self.schema)
            if not row:
                return None
            artifact = _row_to_artifact(row)
            artifact.versions = await self.list_versions(artifact_id)
            return artifact
        except Exception as e:
            logger.error(f"get_artifact({artifact_id}) failed: {e}")
            return None

    async def list_artifacts(
        self,
        *,
        user_id: str,
        scope: ArtifactScope,
        q: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> tuple[List[Artifact], Optional[str], int]:
        """Return (rows, next_cursor, total).

        Cursor is the ISO-8601 ``created_at`` of the last row (keyset
        pagination); ``None`` when there's no next page. Phase 1 keeps this
        simple — Phase 2 may add a richer cursor if perf demands it.
        """
        conditions: list[str] = ["deleted_at IS NULL"]
        params: list = []
        i = 0

        # Scope filter mirrors the frontend store: 'owned' = private/unlisted,
        # 'shared' = org/public. 'all' includes everything the user owns. In
        # Phase 1 we ONLY return artifacts the user owns; cross-org reads land
        # with sharing_service in a follow-up.
        i += 1
        params.append(user_id)
        conditions.append(f"owner_user_id = ${i}")

        if scope == ArtifactScope.OWNED:
            conditions.append("visibility IN ('private', 'unlisted')")
        elif scope == ArtifactScope.SHARED:
            conditions.append("visibility IN ('org', 'public')")

        if q:
            i += 1
            params.append(f"%{q.lower()}%")
            conditions.append(f"LOWER(title) LIKE ${i}")

        if cursor:
            i += 1
            params.append(cursor)
            conditions.append(f"created_at < ${i}::timestamp")

        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) AS n FROM {self.schema}.{self.artifacts_table} WHERE {where_clause}"

        i += 1
        params.append(limit + 1)  # fetch one extra to detect "has next"
        list_sql = f"""
            SELECT * FROM {self.schema}.{self.artifacts_table}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${i}
        """

        async with self.db:
            count_row = await self.db.query_row(count_sql, params[:-1], schema=self.schema)
            rows = await self.db.query(list_sql, params, schema=self.schema)

        total = int(count_row.get("n", 0)) if count_row else 0

        next_cursor: Optional[str] = None
        if len(rows) > limit:
            next_cursor_row = rows[limit - 1]
            created_at = next_cursor_row.get("created_at")
            if isinstance(created_at, datetime):
                next_cursor = created_at.isoformat()
            elif created_at:
                next_cursor = str(created_at)
            rows = rows[:limit]

        artifacts = [_row_to_artifact(r) for r in rows]
        # Listing intentionally skips loading full versions per item — the
        # list view only needs the latest version's metadata, which we pull
        # via a single batch query.
        artifact_ids = [a.id for a in artifacts]
        if artifact_ids:
            placeholders = ",".join(f"${n + 1}" for n in range(len(artifact_ids)))
            v_sql = f"""
                SELECT av.*
                FROM {self.schema}.{self.versions_table} av
                JOIN (
                    SELECT artifact_id, MAX(number) AS max_n
                    FROM {self.schema}.{self.versions_table}
                    WHERE artifact_id IN ({placeholders})
                    GROUP BY artifact_id
                ) latest
                  ON av.artifact_id = latest.artifact_id
                 AND av.number = latest.max_n
            """
            async with self.db:
                v_rows = await self.db.query(v_sql, artifact_ids, schema=self.schema)
            latest_by_id = {v["artifact_id"]: _row_to_version(v) for v in v_rows}
            for a in artifacts:
                latest = latest_by_id.get(a.id)
                if latest is not None:
                    a.versions = [latest]

        return artifacts, next_cursor, total

    async def update_artifact(self, artifact_id: str, fields: dict) -> Optional[Artifact]:
        if not fields:
            return await self.get_artifact(artifact_id)
        set_clauses = []
        params: list = []
        i = 0
        for k, v in fields.items():
            i += 1
            set_clauses.append(f"{k} = ${i}")
            if hasattr(v, "value"):
                params.append(v.value)
            else:
                params.append(v)
        i += 1
        params.append(_now_naive())
        set_clauses.append(f"updated_at = ${i}")
        i += 1
        params.append(artifact_id)
        sql = f"""
            UPDATE {self.schema}.{self.artifacts_table}
            SET {", ".join(set_clauses)}
            WHERE id = ${i} AND deleted_at IS NULL
        """
        async with self.db:
            await self.db.execute(sql, params, schema=self.schema)
        return await self.get_artifact(artifact_id)

    async def set_current_version(self, artifact_id: str, version_id: str) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.artifacts_table}
            SET current_version_id = $1, updated_at = $2
            WHERE id = $3 AND deleted_at IS NULL
        """
        async with self.db:
            count = await self.db.execute(sql, [version_id, _now_naive(), artifact_id], schema=self.schema)
        return bool(count and count > 0)

    async def soft_delete_artifact(self, artifact_id: str, user_id: str) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.artifacts_table}
            SET deleted_at = $1, updated_at = $1
            WHERE id = $2 AND owner_user_id = $3 AND deleted_at IS NULL
        """
        async with self.db:
            count = await self.db.execute(sql, [_now_naive(), artifact_id, user_id], schema=self.schema)
        return bool(count and count > 0)

    # ==================== Versions ====================

    async def add_version(self, artifact_id: str, version: ArtifactVersion) -> ArtifactVersion:
        data = {
            "id": version.id,
            "artifact_id": artifact_id,
            "number": version.number,
            "content": version.content,
            "language": version.language or "",
            "filename": version.filename or "",
            "blob_url": version.blob_url or "",
            "a2ui_state_json": version.a2ui_state_json or None,
            "instruction": version.instruction or "",
            "created_by": version.created_by or "",
            "created_at": _now_naive(),
        }
        async with self.db:
            await self.db.insert_into(self.versions_table, [data], schema=self.schema)
        rows = await self.list_versions(artifact_id)
        for r in rows:
            if r.id == version.id:
                return r
        return version  # pragma: no cover - defensive

    async def list_versions(self, artifact_id: str) -> List[ArtifactVersion]:
        sql = f"""
            SELECT * FROM {self.schema}.{self.versions_table}
            WHERE artifact_id = $1
            ORDER BY number ASC
        """
        try:
            async with self.db:
                rows = await self.db.query(sql, [artifact_id], schema=self.schema)
            return [_row_to_version(r) for r in rows]
        except Exception as e:
            logger.error(f"list_versions({artifact_id}) failed: {e}")
            return []

    async def next_version_number(self, artifact_id: str) -> int:
        sql = f"""
            SELECT COALESCE(MAX(number), 0) AS max_n
            FROM {self.schema}.{self.versions_table}
            WHERE artifact_id = $1
        """
        async with self.db:
            row = await self.db.query_row(sql, [artifact_id], schema=self.schema)
        max_n = int(row.get("max_n", 0)) if row else 0
        return max_n + 1

    # ==================== Health ====================

    async def check_connection(self) -> bool:
        try:
            async with self.db:
                row = await self.db.query_row("SELECT 1 AS ok", [])
            return bool(row)
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    # ==================== Phase 2: artifact_shares ====================
    #
    # Powers POST /publish, POST /revoke, GET /shares, GET /shares/artifacts/{token},
    # and POST /remix (see artifact_service for the business logic).
    #
    # The migration's CHECK constraint limits ``visibility`` to ``public|org``
    # — anything else is rejected at the service layer before we get here.

    @staticmethod
    def _row_to_share(row: dict) -> ArtifactShare:
        cleaned = dict(row)
        if "view_count" in cleaned and cleaned["view_count"] is not None:
            cleaned["view_count"] = int(cleaned["view_count"])
        return ArtifactShare.model_validate(cleaned)

    async def create_share(self, share: ArtifactShare) -> ArtifactShare:
        data = {
            "token": share.token,
            "artifact_id": share.artifact_id,
            "version_pin": share.version_pin,
            "visibility": (
                share.visibility.value if isinstance(share.visibility, ArtifactShareVisibility) else share.visibility
            ),
            "org_id": share.org_id,
            "created_by": share.created_by,
            "expires_at": share.expires_at,
            "revoked_at": None,
            "view_count": 0,
            "created_at": _now_naive(),
        }
        async with self.db:
            await self.db.insert_into("artifact_shares", [data], schema=self.schema)
        fetched = await self.get_share_by_token(share.token)
        if fetched is None:  # pragma: no cover - defensive
            raise RuntimeError(f"insert succeeded but share {share.token} not visible")
        return fetched

    async def get_share_by_token(self, token: str) -> Optional[ArtifactShare]:
        sql = f"""
            SELECT * FROM {self.schema}.artifact_shares
            WHERE token = $1
        """
        try:
            async with self.db:
                row = await self.db.query_row(sql, [token], schema=self.schema)
            if not row:
                return None
            return self._row_to_share(row)
        except Exception as e:
            logger.error(f"get_share_by_token({token}) failed: {e}")
            return None

    async def list_shares_by_artifact(self, artifact_id: str) -> List[ArtifactShare]:
        sql = f"""
            SELECT * FROM {self.schema}.artifact_shares
            WHERE artifact_id = $1
            ORDER BY created_at DESC
        """
        try:
            async with self.db:
                rows = await self.db.query(sql, [artifact_id], schema=self.schema)
            return [self._row_to_share(r) for r in rows]
        except Exception as e:
            logger.error(f"list_shares_by_artifact({artifact_id}) failed: {e}")
            return []

    async def revoke_share(self, artifact_id: str, token: str) -> int:
        """Revoke one share by token. Returns 1 if a row was updated, else 0."""
        sql = f"""
            UPDATE {self.schema}.artifact_shares
            SET revoked_at = $1
            WHERE token = $2 AND artifact_id = $3 AND revoked_at IS NULL
        """
        async with self.db:
            count = await self.db.execute(sql, [_now_naive(), token, artifact_id], schema=self.schema)
        return int(count or 0)

    async def revoke_all_shares(self, artifact_id: str) -> int:
        """Revoke every active share for an artifact. Returns rows-updated."""
        sql = f"""
            UPDATE {self.schema}.artifact_shares
            SET revoked_at = $1
            WHERE artifact_id = $2 AND revoked_at IS NULL
        """
        async with self.db:
            count = await self.db.execute(sql, [_now_naive(), artifact_id], schema=self.schema)
        return int(count or 0)

    async def increment_view_count(self, token: str) -> bool:
        sql = f"""
            UPDATE {self.schema}.artifact_shares
            SET view_count = view_count + 1
            WHERE token = $1
        """
        async with self.db:
            count = await self.db.execute(sql, [token], schema=self.schema)
        return bool(count and count > 0)

    # ==================== Phase 3: runtime usage / quota ====================
    #
    # Per-(artifact,user,UTC-day) row in artifact.artifact_runtime_usage. The
    # service-layer cap check reads ``calls`` for today and 429s when it's
    # already at/over the configured quota. ``record_usage`` performs the
    # atomic upsert so calls always book even under races.

    @staticmethod
    def _today_utc():
        from datetime import timezone

        return datetime.now(timezone.utc).date()

    async def get_today_usage(self, artifact_id: str, user_id: str) -> ArtifactRuntimeUsage:
        """Return today's usage row for the (artifact, user) pair.

        When no row exists for today we return a zeroed view so callers don't
        have to special-case the missing-row branch.
        """
        today = self._today_utc()
        sql = f"""
            SELECT artifact_id, user_id, day_bucket, tokens_in, tokens_out, calls
            FROM {self.schema}.artifact_runtime_usage
            WHERE artifact_id = $1 AND user_id = $2 AND day_bucket = $3
        """
        try:
            async with self.db:
                row = await self.db.query_row(sql, [artifact_id, user_id, today], schema=self.schema)
        except Exception as e:
            logger.error(f"get_today_usage({artifact_id},{user_id}) failed: {e}")
            row = None
        if not row:
            return ArtifactRuntimeUsage(
                artifact_id=artifact_id,
                user_id=user_id,
                day_bucket=today.isoformat(),
                tokens_in=0,
                tokens_out=0,
                calls=0,
            )
        day_bucket = row.get("day_bucket")
        if hasattr(day_bucket, "isoformat"):
            day_bucket = day_bucket.isoformat()
        return ArtifactRuntimeUsage(
            artifact_id=row["artifact_id"],
            user_id=row["user_id"],
            day_bucket=str(day_bucket),
            tokens_in=int(row.get("tokens_in", 0)),
            tokens_out=int(row.get("tokens_out", 0)),
            calls=int(row.get("calls", 0)),
        )

    async def record_usage(
        self,
        artifact_id: str,
        user_id: str,
        tokens_in: int,
        tokens_out: int,
    ) -> ArtifactRuntimeUsage:
        """Atomically increment today's usage row. Inserts on first call."""
        today = self._today_utc()
        now = _now_naive()
        sql = f"""
            INSERT INTO {self.schema}.artifact_runtime_usage
                (artifact_id, user_id, day_bucket, tokens_in, tokens_out, calls, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, 1, $6, $6)
            ON CONFLICT (artifact_id, user_id, day_bucket) DO UPDATE SET
                tokens_in = artifact_runtime_usage.tokens_in + EXCLUDED.tokens_in,
                tokens_out = artifact_runtime_usage.tokens_out + EXCLUDED.tokens_out,
                calls = artifact_runtime_usage.calls + 1,
                updated_at = EXCLUDED.updated_at
            RETURNING artifact_id, user_id, day_bucket, tokens_in, tokens_out, calls
        """
        async with self.db:
            rows = await self.db.query(
                sql,
                [artifact_id, user_id, today, tokens_in, tokens_out, now],
                schema=self.schema,
            )
        row = (rows or [{}])[0]
        day_bucket = row.get("day_bucket")
        if hasattr(day_bucket, "isoformat"):
            day_bucket = day_bucket.isoformat()
        return ArtifactRuntimeUsage(
            artifact_id=row.get("artifact_id", artifact_id),
            user_id=row.get("user_id", user_id),
            day_bucket=str(day_bucket) if day_bucket else today.isoformat(),
            tokens_in=int(row.get("tokens_in", tokens_in)),
            tokens_out=int(row.get("tokens_out", tokens_out)),
            calls=int(row.get("calls", 1)),
        )

    # ==================== Phase 3: MCP grants ====================
    #
    # Backs the approve/call gates. ``find_always_grant`` is the hot path
    # for /mcp/call — when a user has approved a (tool,server) with scope
    # ``always``, every subsequent call short-circuits the prompt. Other
    # scopes intentionally fall through so the gate fires again.

    @staticmethod
    def _row_to_grant(row: dict) -> ArtifactMCPGrant:
        return ArtifactMCPGrant(
            id=row["id"],
            artifact_id=row["artifact_id"],
            user_id=row["user_id"],
            tool_name=row["tool_name"],
            server_id=row["server_id"],
            decision=MCPGrantDecision(row["decision"]),
            scope=MCPGrantScope(row["scope"]),
            approved_at=row.get("approved_at"),
            expires_at=row.get("expires_at"),
            last_used_at=row.get("last_used_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    async def upsert_mcp_grant(self, grant: ArtifactMCPGrant) -> ArtifactMCPGrant:
        """Insert a grant. For (decision=allow,scope=always) the partial unique
        index folds duplicate calls onto a single row; for other scopes we just
        insert a fresh row so audit history stays intact.
        """
        now = _now_naive()
        decision = grant.decision.value if isinstance(grant.decision, MCPGrantDecision) else grant.decision
        scope = grant.scope.value if isinstance(grant.scope, MCPGrantScope) else grant.scope

        if decision == "allow" and scope == "always":
            sql = f"""
                INSERT INTO {self.schema}.artifact_mcp_grants
                    (id, artifact_id, user_id, tool_name, server_id, decision, scope,
                     approved_at, expires_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
                ON CONFLICT (artifact_id, user_id, tool_name, server_id)
                    WHERE decision = 'allow' AND scope = 'always'
                DO UPDATE SET
                    approved_at = EXCLUDED.approved_at,
                    expires_at  = EXCLUDED.expires_at,
                    updated_at  = EXCLUDED.updated_at
                RETURNING *
            """
        else:
            sql = f"""
                INSERT INTO {self.schema}.artifact_mcp_grants
                    (id, artifact_id, user_id, tool_name, server_id, decision, scope,
                     approved_at, expires_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
                RETURNING *
            """
        params = [
            grant.id,
            grant.artifact_id,
            grant.user_id,
            grant.tool_name,
            grant.server_id,
            decision,
            scope,
            grant.approved_at or now,
            grant.expires_at,
            now,
        ]
        async with self.db:
            rows = await self.db.query(sql, params, schema=self.schema)
        if not rows:
            raise RuntimeError("upsert_mcp_grant returned no row")
        return self._row_to_grant(rows[0])

    async def find_always_grant(
        self,
        artifact_id: str,
        user_id: str,
        tool_name: str,
        server_id: str,
    ) -> Optional[ArtifactMCPGrant]:
        """Return an active ``allow``+``always`` grant, or None.

        ``expires_at`` is honoured — expired grants behave as if absent so
        the next /mcp/call falls back to the approval prompt.
        """
        sql = f"""
            SELECT * FROM {self.schema}.artifact_mcp_grants
            WHERE artifact_id = $1 AND user_id = $2 AND tool_name = $3 AND server_id = $4
              AND decision = 'allow' AND scope = 'always'
              AND (expires_at IS NULL OR expires_at > $5)
            ORDER BY approved_at DESC
            LIMIT 1
        """
        try:
            async with self.db:
                row = await self.db.query_row(
                    sql,
                    [artifact_id, user_id, tool_name, server_id, _now_naive()],
                    schema=self.schema,
                )
        except Exception as e:
            logger.error(f"find_always_grant failed: {e}")
            return None
        if not row:
            return None
        return self._row_to_grant(row)

    async def list_grants(self, artifact_id: str, user_id: str) -> List[ArtifactMCPGrant]:
        sql = f"""
            SELECT * FROM {self.schema}.artifact_mcp_grants
            WHERE artifact_id = $1 AND user_id = $2
            ORDER BY approved_at DESC
        """
        try:
            async with self.db:
                rows = await self.db.query(sql, [artifact_id, user_id], schema=self.schema)
            return [self._row_to_grant(r) for r in rows]
        except Exception as e:
            logger.error(f"list_grants({artifact_id},{user_id}) failed: {e}")
            return []

    async def touch_grant_last_used(self, grant_id: str) -> bool:
        sql = f"""
            UPDATE {self.schema}.artifact_mcp_grants
            SET last_used_at = $1, updated_at = $1
            WHERE id = $2
        """
        async with self.db:
            count = await self.db.execute(sql, [_now_naive(), grant_id], schema=self.schema)
        return bool(count and count > 0)

    # ==================== Phase 3: KV storage ====================
    #
    # The PK is (artifact_id, scope, user_id, key); shared rows use the
    # '_shared' sentinel in user_id so the same uniqueness rule covers both
    # scopes. The service layer is responsible for swapping NULL <-> '_shared'
    # before this repo sees the value.

    SHARED_SENTINEL = "_shared"

    @staticmethod
    def _kv_user_key(scope: str, user_id: Optional[str]) -> str:
        return user_id if scope == "personal" else "_shared"

    async def kv_get(
        self,
        artifact_id: str,
        scope: str,
        user_id: Optional[str],
        key: str,
    ) -> Optional[dict]:
        ukey = self._kv_user_key(scope, user_id)
        sql = f"""
            SELECT artifact_id, scope, user_id, key, value, updated_at
            FROM {self.schema}.artifact_kv
            WHERE artifact_id = $1 AND scope = $2 AND user_id = $3 AND key = $4
        """
        try:
            async with self.db:
                row = await self.db.query_row(sql, [artifact_id, scope, ukey, key], schema=self.schema)
        except Exception as e:
            logger.error(f"kv_get({artifact_id},{scope},{key}) failed: {e}")
            return None
        if not row:
            return None
        cleaned = dict(row)
        if "value" in cleaned:
            cleaned["value"] = self._unwrap_kv_value(_to_native(cleaned["value"]))
        return cleaned

    async def kv_put(
        self,
        artifact_id: str,
        scope: str,
        user_id: Optional[str],
        key: str,
        value: Any,
    ) -> dict:
        """Upsert a JSONB row.

        The shared AsyncPostgresClient sets a JSONB codec (json.dumps on
        the way in, json.loads on the way out), so we MUST pass a raw
        Python object here — calling json.dumps ourselves would
        double-encode and we'd read back a JSON string instead of the
        original shape.

        However the dial-down path (gRPC postgres_service) passes params
        through protobuf Struct, which doesn't carry arbitrary scalars
        cleanly. For safety we wrap scalars in a {"_v": value} envelope
        only when the value is NOT a dict/list — but the response layer
        re-unwraps via _maybe_unwrap_scalar below.
        """
        ukey = self._kv_user_key(scope, user_id)
        now = _now_naive()
        payload = self._wrap_kv_value(value)
        sql = f"""
            INSERT INTO {self.schema}.artifact_kv
                (artifact_id, scope, user_id, key, value, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $6)
            ON CONFLICT (artifact_id, scope, user_id, key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at
            RETURNING artifact_id, scope, user_id, key, value, updated_at
        """
        async with self.db:
            rows = await self.db.query(
                sql,
                [artifact_id, scope, ukey, key, payload, now],
                schema=self.schema,
            )
        if not rows:
            raise RuntimeError("kv_put returned no row")
        cleaned = dict(rows[0])
        if "value" in cleaned:
            cleaned["value"] = self._unwrap_kv_value(_to_native(cleaned["value"]))
        return cleaned

    @staticmethod
    def _wrap_kv_value(value: Any) -> Any:
        """Ensure the JSONB codec sees a dict/list (its native shape).

        Scalars (str/int/float/bool/None) get tucked into {"_v": value}
        so we can store them in a JSONB column without surprising the
        gRPC fallback path. The reverse happens in _unwrap_kv_value.
        """
        if isinstance(value, (dict, list)):
            return value
        return {"_v": value}

    @staticmethod
    def _unwrap_kv_value(value: Any) -> Any:
        if isinstance(value, dict) and set(value.keys()) == {"_v"}:
            return value["_v"]
        return value

    async def kv_delete(
        self,
        artifact_id: str,
        scope: str,
        user_id: Optional[str],
        key: str,
    ) -> bool:
        ukey = self._kv_user_key(scope, user_id)
        sql = f"""
            DELETE FROM {self.schema}.artifact_kv
            WHERE artifact_id = $1 AND scope = $2 AND user_id = $3 AND key = $4
        """
        async with self.db:
            count = await self.db.execute(sql, [artifact_id, scope, ukey, key], schema=self.schema)
        return bool(count and count > 0)
