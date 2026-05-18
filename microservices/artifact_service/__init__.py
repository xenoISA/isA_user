"""
Artifact Service

Persistent library of user/org artifacts with versioning, visibility, and
share-link primitives. Backs the Phase 2 frontend in xenoISA/isA_#427 (parent
epic xenoISA/isA_#423 — Claude 2026 SOTA Parity) and replaces the localStorage
stub shipped in xenoISA/isA_#444 (`src/stores/useArtifactLibrary.ts`).

Port: 8291
"""

__version__ = "1.0.0"
__service_name__ = "artifact_service"
__service_port__ = 8291
