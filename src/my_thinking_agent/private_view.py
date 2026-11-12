"""Read-only listing of the configured private knowledge root."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bootstrap import BootstrapError, _configured_knowledge_root


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def private_listing_lines(project_root: Path) -> list[str]:
    """Return a bounded, filename-only overview without reading record bodies."""
    root = _configured_knowledge_root(project_root)
    decisions_root = root / "decisions"
    active = sorted(
        path.name for path in decisions_root.glob("*.md") if path.name != "README.md"
    )
    archive_root = root / ".trash"
    archived = (
        sorted((path.name for path in archive_root.glob("*.md")), reverse=True)
        if archive_root.is_dir()
        else []
    )
    lines = [
        f"private knowledge root: {root}",
        "decision principles: decision-principles.md",
        "active records:",
    ]
    if active:
        lines.extend(f"- {name}" for name in active)
    else:
        lines.append("- （なし）")
    lines.append("archived records:")
    if archived:
        lines.extend(f"- {name}" for name in archived)
    else:
        lines.append("- （なし）")
    lines.append("record本文を確認するには、private knowledge rootをfile managerまたはeditorで開いてください。")
    return lines


def main() -> None:
    """Print the configured private-root overview without modifying it."""
    parser = argparse.ArgumentParser(
        description="List filenames in the configured private knowledge root without reading record bodies."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=_project_root(),
        help="my-thinking-agent checkout to inspect (defaults to this checkout).",
    )
    args = parser.parse_args()
    try:
        print("\n".join(private_listing_lines(args.project_root)))
    except BootstrapError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
