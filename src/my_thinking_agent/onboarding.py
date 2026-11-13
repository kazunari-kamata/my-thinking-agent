"""Interactive, local-first onboarding for private knowledge roots.

The wizard intentionally separates local configuration from external effects.
Creating a GitHub repository and pushing an initial Pull Request each require an
exact confirmation phrase; normal MCP record writes remain separately approved.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from .bootstrap import (
    GENERATED_CONFIG_HEADER,
    BootstrapError,
    initialize_knowledge_root,
    validate_knowledge_root,
    write_project_config,
)


Input = Callable[[str], str]
Output = Callable[[str], None]
CommandRunner = Callable[[Sequence[str], Path], None]
CommandExists = Callable[[str], bool]


class OnboardingError(ValueError):
    """Raised when a guided setup cannot safely continue."""


class OnboardingCancelled(OnboardingError):
    """Raised when the user declines an irreversible external action."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_knowledge_root() -> Path:
    return Path.home() / "my-thinking-agent-private"


def _run_command(command: Sequence[str], cwd: Path) -> None:
    try:
        subprocess.run(list(command), cwd=cwd, check=True)
    except FileNotFoundError as exc:
        raise OnboardingError(f"command is unavailable: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise OnboardingError(
            f"command failed with exit code {exc.returncode}: {shlex.join(command)}"
        ) from exc


def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _ask_path(input_fn: Input, prompt: str, default: Path) -> Path:
    response = input_fn(f"{prompt} [{default}]: ").strip()
    return Path(response).expanduser() if response else default


def _ask_yes_no(input_fn: Input, prompt: str) -> bool:
    return input_fn(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def _require_phrase(input_fn: Input, output: Output, phrase: str) -> None:
    output(f"確認のため、次を完全一致で入力してください: {phrase}")
    if input_fn("> ").strip() != phrase:
        raise OnboardingCancelled("operation cancelled; no external action was performed")


def _require_commands(command_exists: CommandExists, *commands: str) -> None:
    missing = [command for command in commands if not command_exists(command)]
    if missing:
        raise OnboardingError(f"required command is unavailable: {', '.join(missing)}")


def _is_empty_or_metadata_only(root: Path) -> bool:
    if not root.exists():
        return True
    if not root.is_dir():
        return False
    return all(entry.name in {".git", ".jj"} for entry in root.iterdir())


def _ensure_jj_colocation(
    root: Path,
    *,
    output: Output,
    runner: CommandRunner,
    command_exists: CommandExists,
) -> None:
    if not (root / ".git").exists() or (root / ".jj").exists():
        return
    _require_commands(command_exists, "jj")
    _report_and_run(("jj", "git", "init", "--colocate"), root, output, runner)
    _report_and_run(("jj", "bookmark", "track", "main@origin"), root, output, runner)


def _report_and_run(
    command: Sequence[str], root: Path, output: Output, runner: CommandRunner
) -> None:
    output(f"$ (cd {root} && {shlex.join(command)})")
    runner(command, root)


def _initialize_if_safe(
    root: Path, *, input_fn: Input, output: Output
) -> bool:
    """Initialize only an empty destination after an explicit local confirmation."""
    try:
        validate_knowledge_root(root)
        output(f"private knowledge rootを確認しました: {root.expanduser().resolve()}")
        return False
    except BootstrapError:
        pass

    if not _is_empty_or_metadata_only(root):
        raise OnboardingError(
            f"private knowledge root is neither initialized nor empty: {root.expanduser()}"
        )
    output("次のlocal directoryに、判断原則と空のdecisions directoryを作成します。")
    output(f"  {root.expanduser()}")
    _require_phrase(input_fn, output, "INITIALIZE PRIVATE ROOT")
    initialize_knowledge_root(root)
    output(f"private knowledge rootを初期化しました: {root.expanduser().resolve()}")
    return True


def _configure_project(
    project_root: Path, root: Path, *, input_fn: Input, output: Output
) -> None:
    target = project_root / ".codex" / "config.toml"
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if not existing.startswith(GENERATED_CONFIG_HEADER):
            raise OnboardingError(
                f"local Codex configuration is hand-authored and will not be overwritten: {target}"
            )
        if not _ask_yes_no(input_fn, "既存のgenerated MCP設定をこのprivate root向けに更新しますか"):
            output(f"既存のMCP設定を保持します: {target}")
            return
        path = write_project_config(project_root, root, update_generated=True)
        output(f"generated MCP設定を更新しました: {path}")
        return

    path = write_project_config(project_root, root)
    output(f"この端末のMCP設定を作成しました: {path}")


def _publish_initial_template(
    root: Path,
    *,
    input_fn: Input,
    output: Output,
    runner: CommandRunner,
    command_exists: CommandExists,
) -> None:
    if not (root / ".git").exists():
        output("Git repositoryではないため、initial templateのuploadは行いません。")
        return
    if not _ask_yes_no(input_fn, "空のtemplateをprivate Git remoteへPRとしてpushしますか"):
        output("templateはlocalに作成済みです。後でjj workflowからPRを作成できます。")
        return
    _require_commands(command_exists, "jj", "gh")
    output("push対象はdecision-principles.mdとdecisions/README.mdだけです。")
    _require_phrase(input_fn, output, "PUSH INITIAL TEMPLATE")
    commands = (
        ("jj", "status"),
        ("jj", "describe", "-m", "knowledge: initialize private knowledge root"),
        ("jj", "bookmark", "set", "setup/private-knowledge", "-r", "@"),
        ("jj", "git", "push", "--bookmark", "setup/private-knowledge"),
        (
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            "setup/private-knowledge",
            "--title",
            "knowledge: private knowledge rootを初期化",
        ),
    )
    for command in commands:
        _report_and_run(command, root, output, runner)
    output("initial templateのPull Requestを作成しました。merge後に別端末で取得できます。")


def _setup_current_device(
    root: Path,
    *,
    project_root: Path,
    input_fn: Input,
    output: Output,
    runner: CommandRunner,
    command_exists: CommandExists,
    offer_initial_publish: bool,
) -> None:
    initialized = _initialize_if_safe(root, input_fn=input_fn, output=output)
    _ensure_jj_colocation(
        root, output=output, runner=runner, command_exists=command_exists
    )
    _configure_project(project_root, root, input_fn=input_fn, output=output)
    if initialized and offer_initial_publish:
        _publish_initial_template(
            root,
            input_fn=input_fn,
            output=output,
            runner=runner,
            command_exists=command_exists,
        )
    output("次にCodexを再起動し、/mcpでpersonal-knowledgeを確認してください。")


def _create_private_repository(
    root: Path,
    repository_name: str,
    *,
    input_fn: Input,
    output: Output,
    runner: CommandRunner,
    command_exists: CommandExists,
) -> None:
    if not repository_name or any(character.isspace() for character in repository_name):
        raise OnboardingError("repository name must be a non-empty name without whitespace")
    if not _is_empty_or_metadata_only(root):
        raise OnboardingError(f"refusing to create a repository in non-empty directory: {root}")
    _require_commands(command_exists, "git", "gh", "jj")
    output("次のexternal actionを行います。")
    output(f"- GitHub private repositoryを作成: {repository_name}")
    output(f"- local directoryを初期化: {root.expanduser()}")
    output("- 空のmain initial commitをpushし、その後はJJで運用")
    _require_phrase(input_fn, output, "CREATE PRIVATE REPOSITORY")

    root.mkdir(parents=True, exist_ok=True)
    _report_and_run(("git", "init", "-b", "main"), root, output, runner)
    _report_and_run(("git", "commit", "--allow-empty", "-m", "Initial commit"), root, output, runner)
    _report_and_run(
        (
            "gh",
            "repo",
            "create",
            repository_name,
            "--private",
            "--source=.",
            "--remote=origin",
            "--push",
        ),
        root,
        output,
        runner,
    )
    _report_and_run(("jj", "git", "init", "--colocate"), root, output, runner)
    _report_and_run(("jj", "bookmark", "track", "main@origin"), root, output, runner)


def _clone_private_repository(
    repository_url: str,
    root: Path,
    *,
    input_fn: Input,
    output: Output,
    runner: CommandRunner,
    command_exists: CommandExists,
) -> None:
    if not repository_url:
        return
    if root.exists():
        raise OnboardingError(
            f"refusing to clone into an existing directory: {root.expanduser()}"
        )
    _require_commands(command_exists, "git")
    output("次のprivate repositoryをこの端末へcloneします。repository内のdataはこの端末に保存されます。")
    output(f"- remote: {repository_url}")
    output(f"- local: {root.expanduser()}")
    _require_phrase(input_fn, output, "CLONE PRIVATE REPOSITORY")
    root.parent.mkdir(parents=True, exist_ok=True)
    _report_and_run(("git", "clone", repository_url, str(root)), root.parent, output, runner)


def show_status(project_root: Path, output: Output) -> None:
    """Display local-only setup state without changing files or remotes."""
    project = project_root.expanduser().resolve()
    target = project / ".codex" / "config.toml"
    output(f"project: {project}")
    if not target.exists():
        output("MCP設定: 未作成。onboardingでprivate rootを接続できます。")
        return
    generated = target.read_text(encoding="utf-8").startswith(GENERATED_CONFIG_HEADER)
    kind = "bootstrap生成済み" if generated else "手書き設定（上書きしません）"
    output(f"MCP設定: {kind}: {target}")
    output("詳細なMCP状態はCodex起動後に /mcp で確認してください。")


def run_interactive_onboarding(
    *,
    project_root: Path | None = None,
    input_fn: Input = input,
    output: Output = print,
    runner: CommandRunner = _run_command,
    command_exists: CommandExists = _command_exists,
) -> None:
    """Guide one local setup without silently creating remotes or pushing data."""
    project = (project_root or _project_root()).expanduser().resolve()
    output("my-thinking-agent onboarding")
    output("実際の判断記録はprivate rootだけに置きます。external actionは確認後のみ実行します。")
    output("1) この端末だけでprivate rootを初期化・接続する")
    output("2) 既存のprivate repositoryをこの端末へclone・接続する（別端末を含む）")
    output("3) 新しいprivate GitHub repositoryを作成し、初期templateをPRへuploadする")
    output("4) この端末の設定状態だけを確認する")
    choice = input_fn("選択 [1-4, qで終了]: ").strip().lower()
    if choice in {"q", "quit", "exit"}:
        output("onboardingを終了しました。変更はありません。")
        return
    if choice == "4":
        show_status(project, output)
        return
    if choice not in {"1", "2", "3"}:
        raise OnboardingError("select 1, 2, 3, 4, or q")

    root = _ask_path(input_fn, "private knowledge rootのpath", _default_knowledge_root())
    if choice == "3":
        repository_name = input_fn("private GitHub repository名 [my-thinking-agent-private]: ").strip()
        _create_private_repository(
            root,
            repository_name or "my-thinking-agent-private",
            input_fn=input_fn,
            output=output,
            runner=runner,
            command_exists=command_exists,
        )
        _setup_current_device(
            root,
            project_root=project,
            input_fn=input_fn,
            output=output,
            runner=runner,
            command_exists=command_exists,
            offer_initial_publish=True,
        )
        return

    if choice == "2":
        repository_url = input_fn(
            "既存private repositoryのURL（clone済みなら空欄）: "
        ).strip()
        _clone_private_repository(
            repository_url,
            root,
            input_fn=input_fn,
            output=output,
            runner=runner,
            command_exists=command_exists,
        )

    _setup_current_device(
        root,
        project_root=project,
        input_fn=input_fn,
        output=output,
        runner=runner,
        command_exists=command_exists,
        offer_initial_publish=choice == "2",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively initialize or connect private knowledge on this device."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=_project_root(),
        help="my-thinking-agent checkout to configure (defaults to this checkout).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show the local setup state without changing files or remotes.",
    )
    args = parser.parse_args()
    try:
        if args.status:
            show_status(args.project_root, print)
        else:
            run_interactive_onboarding(project_root=args.project_root)
    except OnboardingError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
