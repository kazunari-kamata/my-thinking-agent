from __future__ import annotations

import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from my_thinking_agent.bootstrap import (
    BootstrapError,
    initialize_knowledge_root,
    write_project_config,
)
from my_thinking_agent.knowledge import KnowledgeBase, KnowledgeError
from my_thinking_agent.mcp_server import handle_message
from my_thinking_agent.onboarding import run_interactive_onboarding, show_status


def write_record(root: Path, name: str, classification: str, summary: str) -> None:
    decisions = root / "knowledge" / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    (decisions / f"{name}.md").write_text(
        f"---\nid: {name}\ntitle: {name.title()}\ndate: 2026-01-01\n"
        f"classification: {classification}\ntags: test, reversible\n---\n\n"
        "## Decision\n\nUse a reviewable change.\n\n"
        f"## Summary\n\n{summary}\n",
        encoding="utf-8",
    )


def record_content(
    name: str,
    summary: str,
    *,
    title: str | None = None,
    classification: str = "internal",
) -> str:
    return (
        f"---\nid: {name}\ntitle: {title or name.title()}\ndate: 2026-01-01\n"
        f"classification: {classification}\ntags: test, reversible\n---\n\n"
        "## Decision\n\nUse a reviewable change.\n\n"
        f"## Summary\n\n{summary}\n"
    )


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "knowledge").mkdir()
        (self.root / "knowledge" / "decision-principles.md").write_text(
            "# Principles\n\nPrefer evidence.", encoding="utf-8"
        )
        write_record(
            self.root,
            "internal-record",
            "internal",
            "Prefer a reversible implementation and explicit approval.",
        )
        write_record(
            self.root,
            "confidential-record",
            "confidential",
            "Private material that must not be searchable by default.",
        )
        self.knowledge_base = KnowledgeBase(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_search_returns_matching_allowed_summary_only(self) -> None:
        results = self.knowledge_base.search_decisions("reversible approval")
        self.assertEqual([item["id"] for item in results], ["internal-record"])
        self.assertIn("reversible", results[0]["summary"])

    def test_search_allows_a_term_to_appear_more_than_once(self) -> None:
        results = self.knowledge_base.search_decisions("reversible test")
        self.assertEqual([item["id"] for item in results], ["internal-record"])

    def test_japanese_summary_heading_is_searchable_without_full_body(self) -> None:
        path = self.root / "knowledge" / "decisions" / "japanese-record.md"
        path.write_text(
            "---\nid: japanese-record\ntitle: 日本語の記録\ndate: 2026-01-01\n"
            "classification: internal\ntags: 可逆性\n---\n\n"
            "## 判断\n\n本文には検索結果へ出すべきでない詳細がある。\n\n"
            "## 要約\n\n可逆な手順を優先する。\n",
            encoding="utf-8",
        )
        results = self.knowledge_base.search_decisions("可逆")
        record = next(item for item in results if item["id"] == "japanese-record")
        self.assertEqual(record["summary"], "可逆な手順を優先する。")

    def test_confidential_record_is_unavailable_by_default(self) -> None:
        with self.assertRaisesRegex(KnowledgeError, "not permitted"):
            self.knowledge_base.read_decision("confidential-record")
        self.assertEqual(self.knowledge_base.search_decisions("Private"), [])

    def test_confidential_record_requires_explicit_local_configuration(self) -> None:
        confidential_base = KnowledgeBase(self.root, max_classification="confidential")
        result = confidential_base.read_decision("confidential-record")
        self.assertEqual(result["classification"], "confidential")

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(KnowledgeError, "invalid format"):
            self.knowledge_base.read_decision("../../secret")

    def test_malformed_record_is_not_searchable(self) -> None:
        decisions = self.root / "knowledge" / "decisions"
        (decisions / "malformed.md").write_text("not classified", encoding="utf-8")
        self.assertEqual(self.knowledge_base.search_decisions("classified"), [])

    def test_max_results_is_capped(self) -> None:
        for index in range(12):
            write_record(
                self.root,
                f"record-{index}",
                "internal",
                "A reversible test decision.",
            )
        self.assertEqual(len(self.knowledge_base.search_decisions("reversible", 99)), 10)

    def test_principles_are_readable(self) -> None:
        principles = self.knowledge_base.list_principles()
        self.assertEqual(principles["path"], "decision-principles.md")
        self.assertIn("Prefer evidence", principles["content"])

    def test_external_private_knowledge_root_overrides_project_knowledge(self) -> None:
        private_root = self.root / "private-knowledge"
        (private_root / "decisions").mkdir(parents=True)
        (private_root / "decision-principles.md").write_text(
            "# Private principles\n\nUse only this root.", encoding="utf-8"
        )
        (private_root / "decisions" / "portable.md").write_text(
            "---\nid: portable\ntitle: Portable record\ndate: 2026-01-01\n"
            "classification: internal\ntags: portable\n---\n\n"
            "## Summary\n\nExternal private knowledge only.\n",
            encoding="utf-8",
        )

        private_base = KnowledgeBase(self.root, knowledge_root=private_root)
        self.assertIn("Private principles", private_base.list_principles()["content"])
        self.assertEqual(
            [record["id"] for record in private_base.search_decisions("External")],
            ["portable"],
        )

    def test_create_and_update_require_valid_matching_record_content(self) -> None:
        created = self.knowledge_base.create_decision(
            "new-record", record_content("new-record", "Initial reversible choice.")
        )
        self.assertEqual(created["id"], "new-record")
        self.assertEqual(
            self.knowledge_base.read_decision("new-record")["title"], "New-Record"
        )

        updated = self.knowledge_base.update_decision(
            "new-record",
            record_content(
                "new-record",
                "Updated reversible choice.",
                title="Updated title",
            ),
        )
        self.assertEqual(updated["title"], "Updated title")
        self.assertEqual(
            self.knowledge_base.search_decisions("Updated reversible")[0]["id"],
            "new-record",
        )

        with self.assertRaisesRegex(KnowledgeError, "already exists"):
            self.knowledge_base.create_decision(
                "new-record", record_content("new-record", "Duplicate")
            )
        with self.assertRaisesRegex(KnowledgeError, "front-matter id"):
            self.knowledge_base.update_decision(
                "new-record", record_content("different-record", "Wrong ID")
            )

    def test_public_tutorial_example_is_a_valid_private_record(self) -> None:
        example = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "tutorial-project-priority.md"
        )
        created = self.knowledge_base.create_decision(
            "tutorial-project-priority", example.read_text(encoding="utf-8")
        )
        self.assertEqual(created["id"], "tutorial-project-priority")
        self.assertEqual(created["classification"], "internal")

    def test_delete_archives_and_restore_recovers_without_overwriting(self) -> None:
        archived = self.knowledge_base.delete_decision("internal-record")
        self.assertEqual(archived["operation"], "archived")
        self.assertEqual(self.knowledge_base.search_decisions("reversible"), [])
        archived_records = self.knowledge_base.list_archived_decisions()
        self.assertEqual(archived_records[0]["id"], "internal-record")
        self.assertEqual(archived_records[0]["archive_id"], archived["archive_id"])

        restored = self.knowledge_base.restore_decision(
            "internal-record", archived["archive_id"]
        )
        self.assertEqual(restored["operation"], "restored")
        self.assertEqual(
            self.knowledge_base.search_decisions("reversible")[0]["id"],
            "internal-record",
        )

    def test_delete_respects_classification_boundary(self) -> None:
        with self.assertRaisesRegex(KnowledgeError, "not permitted"):
            self.knowledge_base.delete_decision("confidential-record")

    def test_mutations_refuse_existing_record_with_mismatched_id(self) -> None:
        path = self.root / "knowledge" / "decisions" / "mismatched.md"
        path.write_text(
            record_content("different-record", "Incorrectly named existing record."),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(KnowledgeError, "front-matter id"):
            self.knowledge_base.update_decision(
                "mismatched", record_content("mismatched", "Attempted repair.")
            )
        with self.assertRaisesRegex(KnowledgeError, "front-matter id"):
            self.knowledge_base.delete_decision("mismatched")


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project_root = self.root / "agent"
        self.project_root.mkdir()
        self.knowledge_root = self.root / "private-knowledge"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initialization_and_local_config_keep_data_out_of_project(self) -> None:
        initialized = initialize_knowledge_root(self.knowledge_root)
        config = write_project_config(self.project_root, initialized)
        parsed = tomllib.loads(config.read_text(encoding="utf-8"))
        server = parsed["mcp_servers"]["personal_knowledge"]
        self.assertEqual(server["command"], "uv")
        self.assertEqual(
            server["env"]["MY_THINKING_AGENT_KNOWLEDGE_ROOT"],
            str(self.knowledge_root.resolve()),
        )
        self.assertIn("delete_decision", server["enabled_tools"])
        self.assertFalse((self.project_root / "decision-principles.md").exists())

    def test_initializer_refuses_nonempty_knowledge_root(self) -> None:
        self.knowledge_root.mkdir()
        (self.knowledge_root / "existing.md").write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(BootstrapError, "refusing to overwrite"):
            initialize_knowledge_root(self.knowledge_root)

    def test_initializer_allows_empty_git_and_jj_metadata(self) -> None:
        self.knowledge_root.mkdir()
        (self.knowledge_root / ".git").mkdir()
        (self.knowledge_root / ".jj").mkdir()
        initialized = initialize_knowledge_root(self.knowledge_root)
        self.assertTrue((initialized / "decision-principles.md").is_file())

    def test_config_writer_refuses_to_overwrite_existing_config(self) -> None:
        initialized = initialize_knowledge_root(self.knowledge_root)
        existing = self.project_root / ".codex"
        existing.mkdir()
        (existing / "config.toml").write_text("model = 'example'", encoding="utf-8")
        with self.assertRaisesRegex(BootstrapError, "refusing to overwrite"):
            write_project_config(self.project_root, initialized)

    def test_config_writer_can_update_only_bootstrap_generated_config(self) -> None:
        initialized = initialize_knowledge_root(self.knowledge_root)
        config = write_project_config(self.project_root, initialized)
        updated = write_project_config(
            self.project_root, initialized, update_generated=True
        )
        self.assertEqual(updated, config)
        parsed = tomllib.loads(updated.read_text(encoding="utf-8"))
        self.assertIn(
            "restore_decision",
            parsed["mcp_servers"]["personal_knowledge"]["enabled_tools"],
        )


class OnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project_root = self.root / "agent"
        self.project_root.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def _answers(*values: str):
        responses = iter(values)
        return lambda _prompt: next(responses)

    def test_local_onboarding_initializes_a_root_and_local_config(self) -> None:
        knowledge_root = self.root / "local-private"
        output: list[str] = []
        run_interactive_onboarding(
            project_root=self.project_root,
            input_fn=self._answers("1", str(knowledge_root), "INITIALIZE PRIVATE ROOT"),
            output=output.append,
        )
        self.assertTrue((knowledge_root / "decision-principles.md").is_file())
        self.assertTrue((self.project_root / ".codex" / "config.toml").is_file())
        self.assertIn("private knowledge rootを初期化しました", "\n".join(output))

    def test_existing_private_root_can_be_connected_on_another_device(self) -> None:
        knowledge_root = initialize_knowledge_root(self.root / "existing-private")
        output: list[str] = []
        run_interactive_onboarding(
            project_root=self.project_root,
            input_fn=self._answers("2", str(knowledge_root), ""),
            output=output.append,
        )
        config = (self.project_root / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertIn(str(knowledge_root.resolve()), config)
        self.assertIn("private knowledge rootを確認しました", "\n".join(output))

    def test_new_repository_path_requires_phrases_and_runs_jj_pr_workflow(self) -> None:
        knowledge_root = self.root / "new-private"
        commands: list[tuple[tuple[str, ...], Path]] = []

        def runner(command, cwd):
            normalized = tuple(command)
            commands.append((normalized, cwd))
            if normalized[:3] == ("git", "init", "-b"):
                (cwd / ".git").mkdir()
            if normalized[:3] == ("jj", "git", "init"):
                (cwd / ".jj").mkdir()

        run_interactive_onboarding(
            project_root=self.project_root,
            input_fn=self._answers(
                "3",
                str(knowledge_root),
                "my-thinking-agent-private-test",
                "CREATE PRIVATE REPOSITORY",
                "INITIALIZE PRIVATE ROOT",
                "y",
                "PUSH INITIAL TEMPLATE",
            ),
            output=lambda _message: None,
            runner=runner,
            command_exists=lambda _command: True,
        )
        self.assertTrue((knowledge_root / "decisions" / "README.md").is_file())
        self.assertIn(
            ("gh", "repo", "create", "my-thinking-agent-private-test", "--private", "--source=.", "--remote=origin", "--push"),
            [command for command, _cwd in commands],
        )
        self.assertIn(
            ("gh", "pr", "create", "--base", "main", "--head", "setup/private-knowledge", "--title", "knowledge: private knowledge rootを初期化"),
            [command for command, _cwd in commands],
        )

    def test_existing_repository_can_be_cloned_before_connection(self) -> None:
        knowledge_root = self.root / "cloned-private"
        commands: list[tuple[tuple[str, ...], Path]] = []

        def runner(command, cwd):
            normalized = tuple(command)
            commands.append((normalized, cwd))
            if normalized[:2] == ("git", "clone"):
                knowledge_root.mkdir()
                (knowledge_root / ".git").mkdir()
                initialize_knowledge_root(knowledge_root)
            if normalized[:3] == ("jj", "git", "init"):
                (cwd / ".jj").mkdir()

        run_interactive_onboarding(
            project_root=self.project_root,
            input_fn=self._answers(
                "2",
                str(knowledge_root),
                "https://example.test/private.git",
                "CLONE PRIVATE REPOSITORY",
            ),
            output=lambda _message: None,
            runner=runner,
            command_exists=lambda _command: True,
        )
        self.assertIn(
            ("git", "clone", "https://example.test/private.git", str(knowledge_root)),
            [command for command, _cwd in commands],
        )
        self.assertTrue((self.project_root / ".codex" / "config.toml").is_file())

    def test_status_is_read_only(self) -> None:
        output: list[str] = []
        show_status(self.project_root, output.append)
        self.assertIn("MCP設定: 未作成", "\n".join(output))


class McpProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        (root / "knowledge").mkdir()
        (root / "knowledge" / "decision-principles.md").write_text(
            "# Principles", encoding="utf-8"
        )
        write_record(root, "record", "internal", "Reversible workflow.")
        self.knowledge_base = KnowledgeBase(root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initialize_and_tool_list(self) -> None:
        initialized = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            },
            self.knowledge_base,
        )
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-03-26")

        listed = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, self.knowledge_base
        )
        self.assertEqual(
            {tool["name"] for tool in listed["result"]["tools"]},
            {
                "list_principles",
                "search_decisions",
                "read_decision",
                "create_decision",
                "update_decision",
                "delete_decision",
                "list_archived_decisions",
                "restore_decision",
            },
        )

    def test_tool_call_returns_json_content(self) -> None:
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "search_decisions",
                    "arguments": {"query": "reversible"},
                },
            },
            self.knowledge_base,
        )
        content = response["result"]["content"][0]["text"]
        payload = json.loads(content)
        self.assertEqual(payload[0]["id"], "record")
        self.assertFalse(response["result"]["isError"])

    def test_mutation_tools_require_exact_confirmation_and_archive_is_recoverable(self) -> None:
        content = record_content("created", "Created through MCP.")
        denied = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "create_decision",
                    "arguments": {"id": "created", "content": content, "confirmation": "yes"},
                },
            },
            self.knowledge_base,
        )
        self.assertTrue(denied["result"]["isError"])

        created = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "create_decision",
                    "arguments": {
                        "id": "created",
                        "content": content,
                        "confirmation": "CREATE created",
                    },
                },
            },
            self.knowledge_base,
        )
        self.assertFalse(created["result"]["isError"])

        archived = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "delete_decision",
                    "arguments": {"id": "created", "confirmation": "ARCHIVE created"},
                },
            },
            self.knowledge_base,
        )
        payload = json.loads(archived["result"]["content"][0]["text"])
        self.assertEqual(payload["operation"], "archived")

        restored = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "restore_decision",
                    "arguments": {
                        "id": "created",
                        "archive_id": payload["archive_id"],
                        "confirmation": "RESTORE created",
                    },
                },
            },
            self.knowledge_base,
        )
        self.assertFalse(restored["result"]["isError"])

    def test_unknown_tool_is_a_tool_error(self) -> None:
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "delete_everything", "arguments": {}},
            },
            self.knowledge_base,
        )
        self.assertTrue(response["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
