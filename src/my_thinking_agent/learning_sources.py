"""Bounded, explicitly configured local sources for conversation learning."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


LEARNING_SOURCES_ENV = "MY_THINKING_AGENT_LEARNING_SOURCES"
VALID_SOURCE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
ALLOWED_SUFFIXES = {".md", ".txt", ".log"}
IGNORED_DIRECTORIES = {
    ".git",
    ".jj",
    ".codex",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
}
MAX_SOURCE_FILES = 200
MAX_SOURCE_FILE_BYTES = 256_000
MAX_READ_CHARS = 16_000
MAX_SEARCH_RESULTS = 10
MAX_EXCERPT_CHARS = 700


class LearningSourceError(ValueError):
    """Raised when a configured learning source is unavailable or unsafe."""


def parse_learning_sources(value: str | None) -> dict[str, Path]:
    """Parse the local-only JSON source map without reading any source files."""
    if value is None or not value.strip():
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise LearningSourceError(
            f"{LEARNING_SOURCES_ENV} must be a JSON object"
        ) from exc
    if not isinstance(decoded, dict):
        raise LearningSourceError(f"{LEARNING_SOURCES_ENV} must be a JSON object")

    sources: dict[str, Path] = {}
    for name, raw_path in decoded.items():
        if not isinstance(name, str) or not VALID_SOURCE_NAME.fullmatch(name):
            raise LearningSourceError(
                "learning source names must use lowercase letters, digits, hyphens, or underscores"
            )
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise LearningSourceError(f"learning source {name!r} must have a directory path")
        supplied_path = Path(raw_path).expanduser()
        if not supplied_path.is_absolute():
            raise LearningSourceError(f"learning source {name!r} must use an absolute path")
        path = supplied_path.resolve()
        sources[name] = path
    return sources


def parse_learning_source_specs(
    specifications: list[str] | None, *, base_path: Path
) -> dict[str, Path] | None:
    """Turn NAME=PATH CLI options into paths anchored at the selected project root."""
    if specifications is None:
        return None
    base = base_path.expanduser().resolve()
    sources: dict[str, Path] = {}
    for specification in specifications:
        name, separator, raw_path = specification.partition("=")
        if not separator or not name or not raw_path:
            raise LearningSourceError("--learning-source must use NAME=PATH")
        if not VALID_SOURCE_NAME.fullmatch(name):
            raise LearningSourceError(
                "learning source names must use lowercase letters, digits, hyphens, or underscores"
            )
        if name in sources:
            raise LearningSourceError(f"learning source {name!r} was supplied more than once")
        supplied_path = Path(raw_path).expanduser()
        path = supplied_path if supplied_path.is_absolute() else base / supplied_path
        sources[name] = path.resolve()
    for name, path in sources.items():
        if not path.is_dir():
            raise LearningSourceError(f"learning source {name!r} is not an existing directory: {path}")
    return sources


def parse_learning_source_names(names: Iterable[str] | None) -> tuple[str, ...]:
    """Validate source names used by configuration-removal options."""
    if names is None:
        return ()
    validated: list[str] = []
    for name in names:
        if not VALID_SOURCE_NAME.fullmatch(name):
            raise LearningSourceError(
                "learning source names must use lowercase letters, digits, hyphens, or underscores"
            )
        if name in validated:
            raise LearningSourceError(f"learning source {name!r} was supplied more than once")
        validated.append(name)
    return tuple(validated)


def learning_sources_json(sources: Mapping[str, Path]) -> str:
    """Render a stable source map for the local MCP configuration."""
    return json.dumps(
        {name: str(path.expanduser().resolve()) for name, path in sorted(sources.items())},
        ensure_ascii=False,
        separators=(",", ":"),
    )


class LearningSources:
    """Read only configured, bounded text files under explicitly selected roots."""

    def __init__(self, sources: Mapping[str, Path] | None = None) -> None:
        configured = (
            dict(sources)
            if sources is not None
            else parse_learning_sources(os.environ.get(LEARNING_SOURCES_ENV))
        )
        self.sources = {
            name: Path(path).expanduser().resolve() for name, path in configured.items()
        }

    def list_sources(self) -> list[dict[str, str | bool]]:
        return [
            {
                "name": name,
                "path": str(path),
                "available": path.is_dir(),
            }
            for name, path in sorted(self.sources.items())
        ]

    def search(
        self, query: str, source_names: list[str] | None = None, max_results: int = 5
    ) -> list[dict[str, str]]:
        normalized_query = _validate_query(query)
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise LearningSourceError("max_results must be an integer")
        limit = min(max(1, max_results), MAX_SEARCH_RESULTS)
        selected = self._selected_sources(source_names)
        matches: list[tuple[int, str, str, str]] = []
        for name, root in selected:
            for path in self._text_files(root):
                text = _read_text_file(path)
                if text is None:
                    continue
                score = _match_score(normalized_query, text.lower())
                if score:
                    matches.append(
                        (score, name, path.relative_to(root).as_posix(), _excerpt(text, normalized_query))
                    )
        matches.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [
            {"source": source, "path": path, "excerpt": excerpt}
            for _score, source, path, excerpt in matches[:limit]
        ]

    def read(self, source: str, relative_path: str) -> dict[str, str]:
        root = self._root_for(source)
        path = self._source_file(root, relative_path)
        text = _read_text_file(path)
        if text is None:
            raise LearningSourceError("source file is unavailable, too large, or is not approved text")
        if len(text) > MAX_READ_CHARS:
            text = f"{text[:MAX_READ_CHARS]}\n\n[truncated locally at {MAX_READ_CHARS} characters]"
        return {"source": source, "path": path.relative_to(root).as_posix(), "content": text}

    def validate_references(self, references: Any) -> list[dict[str, str]]:
        if not isinstance(references, list) or not references:
            raise LearningSourceError("source_refs must contain at least one configured source file")
        normalized: list[dict[str, str]] = []
        for reference in references:
            if not isinstance(reference, dict):
                raise LearningSourceError("each source_refs entry must be an object")
            source = reference.get("source")
            relative_path = reference.get("path")
            if not isinstance(source, str) or not isinstance(relative_path, str):
                raise LearningSourceError("each source_refs entry needs string source and path values")
            root = self._root_for(source)
            path = self._source_file(root, relative_path)
            if _read_text_file(path) is None:
                raise LearningSourceError(
                    "referenced source file is unavailable, too large, or is not approved text"
                )
            normalized.append({"source": source, "path": path.relative_to(root).as_posix()})
        return normalized

    def _selected_sources(self, source_names: list[str] | None) -> list[tuple[str, Path]]:
        if source_names is None:
            # A source root can disappear after local configuration (for example an
            # unplugged volume). An all-source search remains useful with the roots
            # that are still available; callers can use list_sources to see the
            # unavailable name. An explicitly named source still fails below.
            return [
                (name, path)
                for name, path in sorted(self.sources.items())
                if path.is_dir()
            ]
        else:
            if not isinstance(source_names, list) or not all(
                isinstance(name, str) for name in source_names
            ):
                raise LearningSourceError("sources must be an array of source names")
            names = source_names
        return [(name, self._root_for(name)) for name in names]

    def _root_for(self, source: str) -> Path:
        if not isinstance(source, str) or source not in self.sources:
            raise LearningSourceError("learning source is not configured")
        root = self.sources[source]
        if not root.is_dir():
            raise LearningSourceError(f"learning source is unavailable: {source}")
        return root

    @staticmethod
    def _text_files(root: Path):
        found = 0
        for current, directories, filenames in os.walk(root):
            directories[:] = [
                directory
                for directory in directories
                if not directory.startswith(".") and directory not in IGNORED_DIRECTORIES
            ]
            current_path = Path(current)
            for filename in sorted(filenames):
                if filename.startswith("."):
                    continue
                path = current_path / filename
                if path.suffix.lower() not in ALLOWED_SUFFIXES:
                    continue
                found += 1
                if found > MAX_SOURCE_FILES:
                    return
                yield path

    @staticmethod
    def _source_file(root: Path, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise LearningSourceError("source path must be relative to its configured root")
        path = (root / candidate).resolve()
        if not path.is_relative_to(root):
            raise LearningSourceError("source path is outside its configured root")
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise LearningSourceError("source file type is not approved")
        return path


def _validate_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise LearningSourceError("query must not be empty")
    normalized = " ".join(query.split()).lower()
    if len(normalized) > 240:
        raise LearningSourceError("query must be at most 240 characters")
    return normalized


def _read_text_file(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_SOURCE_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _match_score(query: str, text: str) -> int:
    terms = query.split()
    if query in text:
        return 100 + text.count(query)
    counts = [text.count(term) for term in terms]
    return sum(counts) if all(counts) else 0


def _excerpt(text: str, query: str) -> str:
    lowered = text.lower()
    position = lowered.find(query)
    if position == -1:
        position = min(
            (candidate for candidate in (lowered.find(term) for term in query.split()) if candidate >= 0),
            default=0,
        )
    start = max(0, position - MAX_EXCERPT_CHARS // 3)
    end = min(len(text), start + MAX_EXCERPT_CHARS)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"
