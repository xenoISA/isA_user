"""K12 audience-line contract helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import DEFAULT_DATA_ROOT

K12_SEED_PATH = DEFAULT_DATA_ROOT / "k12" / "seed.json"


def load_k12_contract(seed_path: Path = K12_SEED_PATH) -> dict[str, Any]:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    return {
        "audienceLine": "k12",
        "seedLocation": "_data/k12/seed.json",
        "noAdultEnterpriseContentByDefault": True,
        "sharedConcepts": [
            "Course",
            "Progress",
            "Quiz",
            "Assistant",
            "Sandbox",
            "Completion Proof",
        ],
        "separateControls": [
            "child_safe_sandbox",
            "age_band_content",
            "teacher_parent_review",
            "assistant_no_answer_dumping",
            "privacy_minimization",
        ],
        "implementationBacklog": [
            {
                "code": "K12-S1",
                "title": "Graphical Agent block editor",
                "priority": "P0",
                "guardrail": "Do not expose adult enterprise workflow primitives.",
            },
            {
                "code": "K12-S2",
                "title": "Child-safe sandbox",
                "priority": "P0",
                "guardrail": "Teacher-approved templates, runtime limits, and audit trail required.",
            },
            {
                "code": "K12-S3",
                "title": "Youth assistant and parent/teacher review",
                "priority": "P1",
                "guardrail": "Guide and encourage; never dump answers or collect unnecessary child data.",
            },
        ],
        "portalStates": seed["portalStates"],
        "firstPblUnit": seed["units"][0],
    }
