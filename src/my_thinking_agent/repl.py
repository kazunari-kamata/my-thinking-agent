"""Small interactive console for setup and local learning-source maintenance."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from .bootstrap import (
    BootstrapError,
    _configured_knowledge_root,
    configured_learning_sources,
    parse_learning_source_names,
    parse_learning_source_specs,
    write_project_config,
)
from .learning_sources import LearningSourceError
from .onboarding import OnboardingError, run_interactive_onboarding, show_status


Input = Callable[[str], str]
Output = Callable[[str], None]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _show_help(output: Output) -> None:
    output("my-thinking-agent repl")
    output("1) 初回設定・別端末設定のonboardingを開く")
    output("2) この端末のMCP設定状態を表示する")
    output("3) learning source一覧と利用可否を表示する")
    output("4) learning sourceを追加・更新する")
    output("5) learning sourceを削除する")
    output("6) 生成済みMCP設定を更新する")
    output("h) このhelpを表示する")
    output("q) 終了する")
    output("source pathはproject rootからの相対pathまたはabsolute pathを指定できます。")


def run_guided_start(
    *,
    project_root: Path | None = None,
    input_fn: Input = input,
    output: Output = print,
) -> None:
    """Walk a first-time user through only the next necessary local step."""
    project = (project_root or _project_root()).expanduser().resolve()
    output("\nはじめて使うための案内を始めます。分からない言葉は気にしなくて大丈夫です。")
    try:
        _configured_knowledge_root(project)
    except BootstrapError:
        output("\nステップ 1 / 3: このPC用の準備をします。")
        output("次の画面では、初めてなら「1」を選んでください。")
        output("ほかのPCで使っているprivate repositoryを使う場合だけ「2」を選びます。")
        try:
            run_interactive_onboarding(project_root=project, input_fn=input_fn, output=output)
        except OnboardingError as exc:
            output(f"準備を完了できませんでした: {exc}")
            output("ここで終了します。後で make start をもう一度実行できます。")
            return
        try:
            _configured_knowledge_root(project)
        except BootstrapError:
            output("準備が完了していないため、ここで終了します。後で make start をもう一度実行できます。")
            return
    else:
        output("\nステップ 1 / 3: このPCの準備は完了しています。")

    output("\nステップ 2 / 3: 学びに使うフォルダを登録しますか？")
    output("登録しなくても使えます。後から追加できます。")
    if input_fn("登録する [y/N]: ").strip().lower() in {"y", "yes"}:
        while True:
            try:
                _add_source(project, input_fn, output)
            except (BootstrapError, LearningSourceError) as exc:
                output(f"sourceを登録できませんでした: {exc}")
                output("このまま使えます。後で make repl から追加できます。")
                break
            if input_fn("ほかにもfolderを登録する [y/N]: ").strip().lower() not in {
                "y",
                "yes",
            }:
                break
    else:
        output("sourceは登録しませんでした。")

    output("\nステップ 3 / 3: これで準備は完了です。")
    output(f"この画面を閉じて、project folder（{project}）で `codex` と入力すると使い始められます。")
    output("困ったときは `make repl`、command一覧は `make help` です。")


def _show_sources(project_root: Path, output: Output) -> None:
    sources = configured_learning_sources(project_root)
    if not sources:
        output("learning sourceは未設定です。")
        return
    for source in sources:
        status = "利用可能" if source["available"] else "利用不可"
        output(f"{source['name']}: {source['path']} ({status})")


def _add_source(project_root: Path, input_fn: Input, output: Output) -> None:
    name = input_fn("source名: ").strip()
    path = input_fn("source path: ").strip()
    source = parse_learning_source_specs([f"{name}={path}"], base_path=project_root)
    root = _configured_knowledge_root(project_root)
    write_project_config(
        project_root, root, update_generated=True, learning_sources=source
    )
    output(f"learning sourceを追加または更新しました: {name}")


def _remove_source(project_root: Path, input_fn: Input, output: Output) -> None:
    name = input_fn("削除するsource名: ").strip()
    names = parse_learning_source_names([name])
    root = _configured_knowledge_root(project_root)
    write_project_config(
        project_root, root, update_generated=True, remove_learning_sources=names
    )
    output(f"learning sourceを削除しました: {name}")


def _update_config(project_root: Path, output: Output) -> None:
    root = _configured_knowledge_root(project_root)
    target = write_project_config(project_root, root, update_generated=True)
    output(f"生成済みMCP設定を更新しました: {target}")


def run_repl(
    *,
    project_root: Path | None = None,
    input_fn: Input = input,
    output: Output = print,
) -> None:
    """Run an explicit, local-only configuration REPL."""
    project = (project_root or _project_root()).expanduser().resolve()
    _show_help(output)
    while True:
        choice = input_fn("選択 [1-6, h, q]: ").strip().lower()
        try:
            if choice in {"q", "quit", "exit"}:
                output("replを終了しました。")
                return
            if choice in {"h", "help", ""}:
                _show_help(output)
            elif choice == "1":
                run_interactive_onboarding(project_root=project, input_fn=input_fn, output=output)
            elif choice == "2":
                show_status(project, output)
            elif choice == "3":
                _show_sources(project, output)
            elif choice == "4":
                _add_source(project, input_fn, output)
            elif choice == "5":
                _remove_source(project, input_fn, output)
            elif choice == "6":
                _update_config(project, output)
            else:
                output("1-6、h、qのいずれかを入力してください。")
        except (BootstrapError, LearningSourceError, OnboardingError) as exc:
            output(f"error: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively manage generated my-thinking-agent local configuration."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=_project_root(),
        help="my-thinking-agent checkout to configure (defaults to this checkout).",
    )
    parser.add_argument(
        "--guided",
        action="store_true",
        help="Guide a first-time user through the next setup steps.",
    )
    args = parser.parse_args()
    if args.guided:
        run_guided_start(project_root=args.project_root)
    else:
        run_repl(project_root=args.project_root)


if __name__ == "__main__":
    main()
