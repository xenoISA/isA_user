"""Read-only course catalog loader for the ``isA_Training`` content source."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .schemas import (
    AudienceLine,
    AudienceLineCode,
    AssetManifest,
    CourseDetail,
    CourseList,
    CoursePath,
    CourseSummary,
    Duration,
    Lesson,
    ManifestAsset,
    Section,
    SourceAsset,
    Track,
)


def _default_data_root() -> Path:
    configured = os.getenv("TRAINING_CONTENT_ROOT")
    if configured:
        return Path(configured)

    # isA_user/microservices/training_service/catalog.py -> isA/
    platform_root = Path(__file__).resolve().parents[3]
    return platform_root / "isA_Training" / "_data"


DEFAULT_DATA_ROOT = _default_data_root()

DIFFICULTY_BY_TRACK = {
    "F": "foundation",
    "B": "applied",
    "T": "advanced",
    "G": "strategic",
    "V": "applied",
}

LESSON_TYPE_BY_ASSET = {
    "pptx": "deck",
    "md": "reading",
    "xlsx": "assessment",
}

AUDIENCE_LINE_ORDER: tuple[AudienceLineCode, ...] = (
    "developer",
    "enterprise",
    "k12",
)

AUDIENCE_LINES = [
    AudienceLine(
        code="developer",
        name="Developer",
        description="Self-serve Agent engineering path with sandbox practice and completion proof.",
        status="available",
    ),
    AudienceLine(
        code="enterprise",
        name="Enterprise",
        description="Organization training line for AI Agent adoption, governance, and white-label delivery.",
        status="available",
    ),
    AudienceLine(
        code="k12",
        name="K12",
        description="PBL and visual AI Agent education for students, parents, and teachers.",
        status="planned",
    ),
]

DEVELOPER_AUDIENCES = {"all", "engineer"}
DEVELOPER_TRACKS = {"F", "T"}
K12_AUDIENCES = {"k12", "student", "students"}


class CourseNotFound(LookupError):
    """Raised when a requested course id is not present in the catalog."""


class CourseCatalog:
    """Load catalog responses from generated JSON without mutating assets."""

    def __init__(self, data_root: Path | str = DEFAULT_DATA_ROOT) -> None:
        self.data_root = Path(data_root)
        self.asset_root = self.data_root.parent

    def list_courses(
        self,
        base_path: str,
        audience_line: AudienceLineCode | None = None,
    ) -> CourseList:
        catalog = self._load_catalog()
        series = catalog.get("series", [])
        courses_by_track: dict[str, list[CourseSummary]] = {
            item["code"]: [] for item in series
        }

        for entry in catalog.get("courses", []):
            course_data = self._load_course_data(entry)
            summary = self._course_summary(entry, course_data, base_path)
            if (
                audience_line is not None
                and audience_line not in summary.supportedAudienceLines
            ):
                continue
            courses_by_track.setdefault(summary.track.code, []).append(summary)

        paths = []
        for item in series:
            track = Track(code=item["code"], name=item["name"])
            courses = courses_by_track.get(track.code, [])
            if audience_line is not None and not courses:
                continue
            total_hours = sum(course.duration.hours for course in courses)
            paths.append(
                CoursePath(
                    code=track.code,
                    name=track.name,
                    track=track,
                    courseCount=len(courses),
                    duration=Duration(hours=total_hours, minutes=total_hours * 60),
                    courses=courses,
                )
            )

        total_courses = sum(path.courseCount for path in paths)
        total_hours = sum(path.duration.hours for path in paths)

        return CourseList(
            platform=str(catalog.get("platform", "isA_Training")),
            totalCourses=total_courses,
            totalHours=total_hours,
            audienceLines=AUDIENCE_LINES,
            paths=paths,
            assetManifest=self._asset_manifest(),
        )

    def get_course(self, course_id: str, base_path: str) -> CourseDetail:
        entry = self._find_course_entry(course_id)
        course_data = self._load_course_data(entry)
        summary = self._course_summary(entry, course_data, base_path)
        source_asset = self._source_asset(str(course_data.get("sourceFile", "")))
        sections = self._sections(course_data, source_asset)
        return CourseDetail(**summary.model_dump(), sections=sections)

    def _load_catalog(self) -> dict[str, Any]:
        return self._read_json(self.data_root / "catalog.json")

    def _load_course_data(self, entry: dict[str, Any]) -> dict[str, Any]:
        course_file = entry.get("courseFile")
        if not course_file:
            return dict(entry)

        course_path = self.data_root / str(course_file)
        if not course_path.exists():
            return dict(entry)

        data = self._read_json(course_path)
        return {**entry, **data}

    def _find_course_entry(self, course_id: str) -> dict[str, Any]:
        course_id = course_id.upper()
        for entry in self._load_catalog().get("courses", []):
            if str(entry.get("code", "")).upper() == course_id:
                return entry
        raise CourseNotFound(f"Course not found: {course_id}")

    def _course_summary(
        self,
        entry: dict[str, Any],
        course_data: dict[str, Any],
        base_path: str,
    ) -> CourseSummary:
        code = str(course_data.get("code") or entry.get("code"))
        series = str(course_data.get("series") or entry.get("series"))
        series_name = str(course_data.get("seriesName") or entry.get("seriesName"))
        duration_hours = int(
            course_data.get("durationHours") or entry.get("durationHours") or 0
        )
        source_file = str(course_data.get("sourceFile", ""))
        asset_type = self._asset_type(source_file)

        return CourseSummary(
            id=code,
            course=str(course_data.get("title") or entry.get("title") or code),
            track=Track(code=series, name=series_name),
            role=str(course_data.get("audience") or entry.get("audience") or "all"),
            supportedAudienceLines=self._supported_audience_lines(entry, course_data),
            duration=Duration(hours=duration_hours, minutes=duration_hours * 60),
            difficulty=str(
                course_data.get("difficulty")
                or entry.get("difficulty")
                or DIFFICULTY_BY_TRACK.get(series, "general")
            ),
            lessonType=LESSON_TYPE_BY_ASSET.get(asset_type, "asset"),
            sourceAsset=self._source_asset(source_file),
            slideCount=self._optional_int(course_data.get("slideCount")),
            notesCoverage=course_data.get("notesCoverage"),
            sectionsUrl=f"{base_path}/courses/{code}",
        )

    def _sections(
        self,
        course_data: dict[str, Any],
        source_asset: SourceAsset,
    ) -> list[Section]:
        code = str(course_data.get("code"))
        slides = sorted(
            course_data.get("slides", []),
            key=lambda slide: int(slide.get("n", 0)),
        )
        lesson_minutes = self._lesson_minutes(course_data, len(slides))

        sections: list[Section] = []
        current: Section | None = None
        for slide in slides:
            if self._is_section_marker(slide):
                current = Section(
                    id=f"{code}-S{len(sections) + 1}",
                    section=self._section_title(slide),
                    ordinal=len(sections) + 1,
                    lessons=[],
                )
                sections.append(current)
            elif current is None:
                current = Section(
                    id=f"{code}-S0",
                    section="Course Overview",
                    ordinal=0,
                    lessons=[],
                )
                sections.append(current)

            current.lessons.append(
                self._lesson(code, slide, lesson_minutes, source_asset)
            )

        return sections

    def _lesson(
        self,
        course_code: str,
        slide: dict[str, Any],
        lesson_minutes: int,
        source_asset: SourceAsset,
    ) -> Lesson:
        slide_number = int(slide.get("n", 0))
        return Lesson(
            id=f"{course_code}-L{slide_number}",
            lesson=self._lesson_title(slide),
            lessonType=self._lesson_type(slide),
            slideNumber=slide_number,
            duration=Duration(hours=lesson_minutes // 60, minutes=lesson_minutes),
            sourceAsset=source_asset,
            body=str(slide.get("body") or ""),
            notes=str(slide.get("notes") or ""),
        )

    def _asset_manifest(self) -> AssetManifest:
        manifest_path = self.data_root / "manifest.json"
        if not manifest_path.exists():
            return AssetManifest(machineReadable={}, humanAssets=[])

        manifest = self._read_json(manifest_path)
        human_assets = [
            ManifestAsset(
                key=str(key),
                value=str(value),
                type=self._asset_type(str(value)),
            )
            for key, value in manifest.get("humanAssets", {}).items()
        ]
        return AssetManifest(
            machineReadable={
                str(key): str(value)
                for key, value in manifest.get("machineReadable", {}).items()
            },
            humanAssets=human_assets,
        )

    def _source_asset(self, source_file: str) -> SourceAsset:
        asset_type = self._asset_type(source_file)
        if not source_file:
            return SourceAsset(
                path="",
                type=asset_type,
                available=False,
                status="unavailable",
                reason="source asset not declared",
            )

        available = (self.asset_root / source_file).exists()
        return SourceAsset(
            path=source_file,
            type=asset_type,
            available=available,
            status="available" if available else "unavailable",
            reason=None if available else "source asset not found",
        )

    def _supported_audience_lines(
        self,
        entry: dict[str, Any],
        course_data: dict[str, Any],
    ) -> list[AudienceLineCode]:
        explicit = (
            course_data.get("supportedAudienceLines")
            or course_data.get("audienceLines")
            or entry.get("supportedAudienceLines")
            or entry.get("audienceLines")
        )
        if isinstance(explicit, list):
            return self._sort_audience_lines(str(item) for item in explicit)

        series = str(course_data.get("series") or entry.get("series") or "").upper()
        audience = str(
            course_data.get("audience") or entry.get("audience") or ""
        ).lower()

        if audience in K12_AUDIENCES or series.startswith("K"):
            return ["k12"]

        lines: list[AudienceLineCode] = ["enterprise"]
        if audience in DEVELOPER_AUDIENCES or series in DEVELOPER_TRACKS:
            lines.append("developer")
        return self._sort_audience_lines(lines)

    def _sort_audience_lines(self, values: Any) -> list[AudienceLineCode]:
        value_set = {str(value) for value in values}
        return [line for line in AUDIENCE_LINE_ORDER if line in value_set]

    def _lesson_minutes(self, course_data: dict[str, Any], lesson_count: int) -> int:
        duration_hours = int(course_data.get("durationHours") or 0)
        if lesson_count <= 0 or duration_hours <= 0:
            return 0
        return max(1, round((duration_hours * 60) / lesson_count))

    def _is_section_marker(self, slide: dict[str, Any]) -> bool:
        return str(slide.get("title") or "").strip().startswith("SECTION ")

    def _section_title(self, slide: dict[str, Any]) -> str:
        lines = [
            line.strip()
            for line in str(slide.get("body") or "").splitlines()
            if line.strip()
        ]
        if len(lines) > 1 and lines[0].startswith("SECTION "):
            return lines[1]
        return str(slide.get("title") or "Section")

    def _lesson_title(self, slide: dict[str, Any]) -> str:
        title = str(slide.get("title") or "").strip()
        if title:
            return title

        body = str(slide.get("body") or "")
        for line in body.splitlines():
            if line.strip():
                return line.strip()
        return f"Slide {slide.get('n', '')}".strip()

    def _lesson_type(self, slide: dict[str, Any]) -> str:
        title = str(slide.get("title") or "")
        body = str(slide.get("body") or "")
        text = f"{title}\n{body}".upper()
        if self._is_section_marker(slide):
            return "section-overview"
        if "AGENDA" in text:
            return "agenda"
        if "回顾" in text or "CHEAT SHEET" in text or "结业" in text:
            return "review"
        return "slide"

    def _asset_type(self, value: str) -> str:
        matches = re.findall(r"\.([A-Za-z0-9]+)", value)
        if not matches:
            return "unknown"
        return matches[-1].lower()

    def _optional_int(self, value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
