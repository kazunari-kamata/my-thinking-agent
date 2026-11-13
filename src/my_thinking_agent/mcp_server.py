"""A minimal, dependency-free MCP server over stdio."""

from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .knowledge import KnowledgeBase, KnowledgeError


SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
SERVER_INSTRUCTIONS = (
    "Search before reading full records and cite record IDs. Create, update, "
    "archive, and restore tools require the exact per-action confirmation value. "
    "Never mutate a record unless the user explicitly approves that operation. "
    "Mutations are local only; this server never commits, pushes, or contacts "
    "external systems."
)


TOOLS = [
    {
        "name": "list_principles",
        "description": "Read the concise, durable decision principles for this project.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "search_decisions",
        "description": (
            "Search locally stored, classification-permitted decision records. "
            "Returns metadata and a short Summary section, not full records."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms for comparable precedents.",
                    "minLength": 1,
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_decision",
        "description": (
            "Read one classification-permitted record by its exact ID. "
            "Use search_decisions first whenever possible."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The exact ID returned by search_decisions.",
                    "minLength": 1,
                }
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_decision",
        "description": (
            "Create one local decision record. Requires confirmation exactly "
            "equal to CREATE <id>. The record is not committed or pushed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "content": {
                    "type": "string",
                    "description": "Complete Markdown record, including validated front matter.",
                    "minLength": 1,
                },
                "confirmation": {"type": "string", "minLength": 1},
            },
            "required": ["id", "content", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_decision",
        "description": (
            "Atomically replace one local record. Requires confirmation exactly "
            "equal to UPDATE <id>. The record id cannot change."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "content": {
                    "type": "string",
                    "description": "Complete replacement Markdown record with the same front-matter id.",
                    "minLength": 1,
                },
                "confirmation": {"type": "string", "minLength": 1},
            },
            "required": ["id", "content", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_decision",
        "description": (
            "Remove one record from active retrieval by moving it to .trash. "
            "Requires confirmation exactly equal to ARCHIVE <id>. It is recoverable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "confirmation": {"type": "string", "minLength": 1},
            },
            "required": ["id", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_archived_decisions",
        "description": "List locally archived records that can be restored.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "restore_decision",
        "description": (
            "Restore one archived local record. Requires confirmation exactly "
            "equal to RESTORE <id> and never overwrites an active record."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "archive_id": {"type": "string", "minLength": 1},
                "confirmation": {"type": "string", "minLength": 1},
            },
            "required": ["id", "archive_id", "confirmation"],
            "additionalProperties": False,
        },
    },
]


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _content(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
            }
        ],
        "isError": is_error,
    }


def _protocol_version(params: dict[str, Any]) -> str:
    requested = params.get("protocolVersion")
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return SUPPORTED_PROTOCOL_VERSIONS[0]


def handle_message(message: dict[str, Any], knowledge_base: KnowledgeBase) -> dict[str, Any] | None:
    """Handle one JSON-RPC request. Notifications intentionally return nothing."""
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(message.get("id"), -32600, "Invalid JSON-RPC request")

    method = message["method"]
    message_id = message.get("id")
    if "id" not in message:
        return None
    params = message.get("params", {})
    if not isinstance(params, dict):
        return _error(message_id, -32602, "params must be an object")

    if method == "initialize":
        return _result(
            message_id,
            {
                "protocolVersion": _protocol_version(params),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "personal-knowledge", "version": __version__},
                "instructions": SERVER_INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _result(message_id, {})
    if method == "tools/list":
        return _result(message_id, {"tools": TOOLS})
    if method == "tools/call":
        return _tool_call(message_id, params, knowledge_base)
    return _error(message_id, -32601, f"Method not found: {method}")


def _tool_call(
    message_id: Any, params: dict[str, Any], knowledge_base: KnowledgeBase
) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return _result(message_id, _content({"error": "invalid tool request"}, is_error=True))

    try:
        if name == "list_principles":
            payload = knowledge_base.list_principles()
        elif name == "search_decisions":
            payload = knowledge_base.search_decisions(
                arguments.get("query", ""), arguments.get("max_results", 5)
            )
        elif name == "read_decision":
            payload = knowledge_base.read_decision(arguments.get("id", ""))
        elif name == "create_decision":
            identifier = arguments.get("id", "")
            _require_confirmation(arguments, f"CREATE {identifier}")
            payload = knowledge_base.create_decision(identifier, arguments.get("content", ""))
        elif name == "update_decision":
            identifier = arguments.get("id", "")
            _require_confirmation(arguments, f"UPDATE {identifier}")
            payload = knowledge_base.update_decision(identifier, arguments.get("content", ""))
        elif name == "delete_decision":
            identifier = arguments.get("id", "")
            _require_confirmation(arguments, f"ARCHIVE {identifier}")
            payload = knowledge_base.delete_decision(identifier)
        elif name == "list_archived_decisions":
            payload = knowledge_base.list_archived_decisions()
        elif name == "restore_decision":
            identifier = arguments.get("id", "")
            _require_confirmation(arguments, f"RESTORE {identifier}")
            payload = knowledge_base.restore_decision(
                identifier, arguments.get("archive_id", "")
            )
        else:
            return _result(message_id, _content({"error": "unknown tool"}, is_error=True))
    except KnowledgeError as exc:
        return _result(message_id, _content({"error": str(exc)}, is_error=True))
    return _result(message_id, _content(payload))


def _require_confirmation(arguments: dict[str, Any], expected: str) -> None:
    if arguments.get("confirmation") != expected:
        raise KnowledgeError(
            f"explicit confirmation is required; confirmation must equal: {expected}"
        )


def main() -> None:
    """Serve newline-delimited JSON-RPC on stdin/stdout without logging content."""
    knowledge_base = KnowledgeBase()
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        try:
            message = json.loads(raw_line)
            if not isinstance(message, dict):
                raise ValueError("request must be a JSON object")
        except (json.JSONDecodeError, ValueError) as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
        else:
            response = handle_message(message, knowledge_base)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
