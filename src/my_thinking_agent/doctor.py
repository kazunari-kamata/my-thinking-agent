"""Check the local commands needed by the guided setup without changing data."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable


CommandExists = Callable[[str], bool]

REQUIRED_COMMANDS = ("uv", "git", "codex")
OPTIONAL_COMMANDS = ("jj", "gh")


def missing_requirements(
    *,
    command_exists: CommandExists = lambda command: shutil.which(command) is not None,
    python_version: tuple[int, int] = sys.version_info[:2],
) -> list[str]:
    """Return only missing requirements so callers can display a short next step."""
    missing: list[str] = []
    if python_version < (3, 11):
        missing.append("Python 3.11以上")
    missing.extend(command for command in REQUIRED_COMMANDS if not command_exists(command))
    return missing


def main() -> None:
    """Print a beginner-friendly, read-only local environment check."""
    missing = missing_requirements()
    print("my-thinking-agent: 使い始める前の確認")
    print(f"Python: {sys.version.split()[0]}")
    if missing:
        print("まだ準備が必要です: " + ", ".join(missing))
        print("不足したcommandをinstallしてから、もう一度 `make doctor` を実行してください。")
        raise SystemExit(2)

    print("必要なPython、uv、Git、Codex commandを確認しました。")
    optional_missing = [
        command for command in OPTIONAL_COMMANDS if shutil.which(command) is None
    ]
    if optional_missing:
        print(
            "補足: "
            + ", ".join(optional_missing)
            + " は、複数端末でprivate repositoryを使う場合だけ必要です。"
        )
    print("次は `make start` を入力してください。")


if __name__ == "__main__":
    main()
