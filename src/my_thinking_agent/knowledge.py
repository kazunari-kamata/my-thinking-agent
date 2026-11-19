"""Safe local access to classified decision records and recoverable CRUD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import tempfile
from typing import Any


CLASSIFICATION_RANK = {"public": 0, "internal": 1, "confidential": 2}
DEFAULT_MAX_CLASSIFICATION = "internal"
MAX_DOCUMENT_CHARS = 16_000
MAX_SEARCH_RESULTS = 10
VALID_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
ARCHIVE_NAME = re.compile(
    r"^(?P<id>[a-z0-9][a-z0-9_-]{0,79})--"
    r"(?P<timestamp>\d{8}T\d{6}Z)(?:-(?P<suffix>\d+))?\.md$"
)
TRASH_DIRECTORY = ".trash"


class KnowledgeError(ValueError):
    """Raised when a requested record is unavailable or unsafe to expose."""


@dataclass(frozen=True)
class DecisionRecord:
    """A decision record whose metadata has passed the local access policy."""

    identifier: str
    title: str
    date: str
    classification: str
    tags: str
    body: str
    path: Path

    def summary(self) -> str:
        """Return the short, explicit summary section when available."""
        match = re.search(
            r"(?ms)^## (?:Summary|要約)\s*$\n(?P<summary>.*?)(?=^##\s|\Z)",
            self.body,
        )
        if match:
            return _bounded_text(match.group("summary").strip(), 1_200)
        return _bounded_text(self.body.strip(), 1_200)


def _bounded_text(value: str, limit: int = MAX_DOCUMENT_CHARS) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n\n[truncated locally at {limit} characters]"


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Parse the intentionally small front-matter subset used by this project."""
    if not text.startswith("---\n"):
        raise KnowledgeError("record has no front matter")
    closing = text.find("\n---\n", 4)
    if closing == -1:
        raise KnowledgeError("record front matter is not closed")

    metadata: dict[str, str] = {}
    for line in text[4:closing].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise KnowledgeError("record front matter contains an invalid line")
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, text[closing + len("\n---\n") :]


class KnowledgeBase:
    """Expose only classified records underneath a fixed local root."""

    def __init__(
        self,
        project_root: Path | None = None,
        knowledge_root: Path | None = None,
        max_classification: str | None = None,
    ) -> None:
        default_root = Path(__file__).resolve().parents[2]
        self.project_root = (project_root or default_root).resolve()
        configured_root = knowledge_root or os.environ.get(
            "MY_THINKING_AGENT_KNOWLEDGE_ROOT"
        )
        self.knowledge_root = (
            Path(configured_root).expanduser().resolve()
            if configured_root
            else (self.project_root / "knowledge").resolve()
        )
        self.decisions_root = (self.knowledge_root / "decisions").resolve()
        requested = max_classification or os.environ.get(
            "MY_THINKING_AGENT_MAX_CLASSIFICATION", DEFAULT_MAX_CLASSIFICATION
        )
        self.max_classification = requested.strip().lower()
        if self.max_classification not in CLASSIFICATION_RANK:
            allowed = ", ".join(CLASSIFICATION_RANK)
            raise KnowledgeError(
                "MY_THINKING_AGENT_MAX_CLASSIFICATION must be one of: " f"{allowed}"
            )

    def list_principles(self) -> dict[str, str]:
        path = (self.knowledge_root / "decision-principles.md").resolve()
        if not path.is_file() or not path.is_relative_to(self.knowledge_root):
            raise KnowledgeError("decision principles file is unavailable")
        return {
            "path": "decision-principles.md",
            "content": _bounded_text(path.read_text(encoding="utf-8")),
        }

    def search_decisions(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            raise KnowledgeError("query must not be empty")
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise KnowledgeError("max_results must be an integer")
        max_results = min(max(1, max_results), MAX_SEARCH_RESULTS)

        matches: list[tuple[int, DecisionRecord]] = []
        for record in self._records():
            haystack = "\n".join(
                [record.identifier, record.title, record.tags, record.summary()]
            ).lower()
            score = _match_score(normalized_query, haystack)
            if score:
                matches.append((score, record))

        matches.sort(key=lambda item: (-item[0], item[1].date, item[1].identifier))
        return [
            {
                "id": record.identifier,
                "title": record.title,
                "date": record.date,
                "classification": record.classification,
                "tags": record.tags,
                "summary": record.summary(),
            }
            for _, record in matches[:max_results]
        ]

    def read_decision(self, identifier: str) -> dict[str, str]:
        path = self._decision_path(identifier)
        if not path.is_file():
            raise KnowledgeError("record not found")
        record = self._read_record(path)
        self._assert_identifier_matches_path(record, identifier)
        return {
            "id": record.identifier,
            "title": record.title,
            "date": record.date,
            "classification": record.classification,
            "tags": record.tags,
            "content": _bounded_text(record.body),
        }

    def create_decision(self, identifier: str, content: str) -> dict[str, str]:
        """Create one validated record without overwriting an existing record."""
        path = self._decision_path(identifier)
        if path.exists():
            raise KnowledgeError("record already exists; use update_decision instead")
        record = self._record_from_content(path, content)
        self._assert_identifier_matches_path(record, identifier)
        self._atomic_write(path, content)
        return self._record_metadata(record)

    def update_decision(self, identifier: str, content: str) -> dict[str, str]:
        """Atomically replace one existing, classification-permitted record."""
        path = self._decision_path(identifier)
        if not path.is_file():
            raise KnowledgeError("record not found")
        current = self._read_record(path)
        self._assert_identifier_matches_path(current, identifier)
        record = self._record_from_content(path, content)
        self._assert_identifier_matches_path(record, identifier)
        self._atomic_write(path, content)
        return self._record_metadata(record)

    def delete_decision(self, identifier: str) -> dict[str, str]:
        """Remove a record from active retrieval by moving it to local trash."""
        path = self._decision_path(identifier)
        if not path.is_file():
            raise KnowledgeError("record not found")
        record = self._read_record(path)
        self._assert_identifier_matches_path(record, identifier)
        trash_root = self._trash_root(create=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = trash_root / f"{record.identifier}--{timestamp}.md"
        suffix = 1
        while archived.exists():
            archived = trash_root / f"{record.identifier}--{timestamp}-{suffix}.md"
            suffix += 1
        os.replace(path, archived)
        return {
            **self._record_metadata(record),
            "archive_id": archived.name,
            "operation": "archived",
        }

    def list_archived_decisions(self) -> list[dict[str, str]]:
        """List recoverable archived records without reading their contents."""
        trash_root = self._trash_root(create=False)
        if not trash_root.is_dir():
            return []
        archived: list[dict[str, str]] = []
        for path in sorted(trash_root.glob("*.md"), reverse=True):
            match = ARCHIVE_NAME.fullmatch(path.name)
            if match:
                archived.append(
                    {
                        "id": match.group("id"),
                        "archive_id": path.name,
                        "archived_at": match.group("timestamp"),
                    }
                )
        return archived

    def restore_decision(self, identifier: str, archive_id: str) -> dict[str, str]:
        """Restore an archived record only when no active record would be replaced."""
        self._validate_identifier(identifier)
        if not isinstance(archive_id, str):
            raise KnowledgeError("archive_id has an invalid format")
        match = ARCHIVE_NAME.fullmatch(archive_id)
        if not match or match.group("id") != identifier:
            raise KnowledgeError("archive_id does not belong to the requested record")
        trash_root = self._trash_root(create=False)
        archived = (trash_root / archive_id).resolve()
        if not archived.is_relative_to(trash_root) or not archived.is_file():
            raise KnowledgeError("archived record not found")
        target = self._decision_path(identifier)
        if target.exists():
            raise KnowledgeError("active record already exists; refusing to overwrite it")
        record = self._record_from_content(archived, archived.read_text(encoding="utf-8"))
        self._assert_identifier_matches_path(record, identifier)
        os.replace(archived, target)
        return {**self._record_metadata(record), "operation": "restored"}

    def _decision_path(self, identifier: str) -> Path:
        self._validate_identifier(identifier)
        if not self.decisions_root.is_dir():
            raise KnowledgeError("decisions directory is unavailable")
        path = (self.decisions_root / f"{identifier}.md").resolve()
        if not path.is_relative_to(self.decisions_root):
            raise KnowledgeError("record path is outside the decisions directory")
        return path

    def _trash_root(self, *, create: bool) -> Path:
        candidate = self.knowledge_root / TRASH_DIRECTORY
        if create:
            candidate.mkdir(exist_ok=True)
        root = candidate.resolve()
        if not root.is_relative_to(self.knowledge_root):
            raise KnowledgeError("trash directory is outside the knowledge root")
        return root

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if not isinstance(identifier, str) or not VALID_ID.fullmatch(identifier):
            raise KnowledgeError("id has an invalid format")

    @staticmethod
    def _assert_identifier_matches_path(record: DecisionRecord, identifier: str) -> None:
        if record.identifier != identifier:
            raise KnowledgeError("record filename and front-matter id do not match")

    @staticmethod
    def _record_metadata(record: DecisionRecord) -> dict[str, str]:
        return {
            "id": record.identifier,
            "title": record.title,
            "date": record.date,
            "classification": record.classification,
            "tags": record.tags,
            "summary": record.summary(),
        }

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        if not isinstance(content, str):
            raise KnowledgeError("content must be a string")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, delete=False
            ) as temporary:
                temporary.write(f"{content.rstrip()}\n")
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, path)
        except OSError as exc:
            raise KnowledgeError(f"unable to write record safely: {exc}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _records(self) -> list[DecisionRecord]:
        if not self.decisions_root.is_dir():
            return []
        records: list[DecisionRecord] = []
        for path in sorted(self.decisions_root.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                records.append(self._read_record(path))
            except KnowledgeError:
                # An unclassified or malformed record is deliberately invisible.
                continue
        return records

    def _read_record(self, path: Path) -> DecisionRecord:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.decisions_root) or not resolved.is_file():
            raise KnowledgeError("record path is outside the decisions directory")
        return self._record_from_content(resolved, resolved.read_text(encoding="utf-8"))

    def _record_from_content(self, path: Path, content: str) -> DecisionRecord:
        if not isinstance(content, str):
            raise KnowledgeError("content must be a string")
        metadata, body = _parse_front_matter(content)
        required = ("id", "title", "date", "classification")
        missing = [key for key in required if not metadata.get(key)]
        if missing:
            raise KnowledgeError(f"record is missing required metadata: {', '.join(missing)}")

        identifier = metadata["id"].lower()
        classification = metadata["classification"].lower()
        if not VALID_ID.fullmatch(identifier):
            raise KnowledgeError("record id has an invalid format")
        if classification not in CLASSIFICATION_RANK:
            raise KnowledgeError("record classification is invalid")
        if CLASSIFICATION_RANK[classification] > CLASSIFICATION_RANK[self.max_classification]:
            raise KnowledgeError("record classification is not permitted in this session")

        return DecisionRecord(
            identifier=identifier,
            title=metadata["title"],
            date=metadata["date"],
            classification=classification,
            tags=metadata.get("tags", ""),
            body=body.strip(),
            path=path,
        )


def _match_score(query: str, haystack: str) -> int:
    """Use predictable local substring matching instead of opaque ranking."""
    terms = [term for term in re.split(r"\s+", query) if term]
    if not terms:
        return 0
    if query in haystack:
        return 100 + haystack.count(query)
    counts = [haystack.count(term) for term in terms]
    return sum(counts) if all(counts) else 0
