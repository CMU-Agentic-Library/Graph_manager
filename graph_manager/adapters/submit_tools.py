"""Stdio MCP server with the two submit tools; Harness starts one per session.

    python -m graph_manager.adapters.submit_tools --zenobench-root PATH

submit_plan validates the plan against the skill catalog and returns every issue as a tool
error, so the model can fix the plan within the same turn. submit_decision accepts
continue or finish. Whether continue is allowed after a failed subgoal is checked by the
closed loop, which knows how the last subgoal went.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from ..domain.models import ProposalValidationError
from ..domain.skills import SkillCatalog
from ..domain.submission import DECISION_SCHEMA, DECISION_TOOL, PLAN_TOOL, plan_schema
from ..domain.task_plan import validate_task_plan
from .zenobench_library import DEFAULT_ROOT, ZenoBenchLibrary

ACCEPTED = "Accepted. Your answer is recorded; end your turn now."
DEFAULT_PROTOCOL = "2025-06-18"
PLAN_DESCRIPTION = (
    "Submit a complete task_plan: the whole plan at the start of a task, or only the "
    "remaining work when you replan. If it is rejected, fix every listed error and call "
    "this tool again."
)
DECISION_DESCRIPTION = (
    'After a subgoal: {"kind": "continue"} runs the next planned subgoal unchanged; '
    '{"kind": "finish"} ends the task.'
)


def tool_definitions(catalog: SkillCatalog) -> list[dict]:
    verbs = sorted(skill.verb for skill in catalog.skills)
    return [
        {"name": PLAN_TOOL, "description": PLAN_DESCRIPTION, "inputSchema": plan_schema(verbs)},
        {
            "name": DECISION_TOOL,
            "description": DECISION_DESCRIPTION,
            "inputSchema": DECISION_SCHEMA,
        },
    ]


def call_tool(name: object, arguments: object, catalog: SkillCatalog) -> tuple[str, bool]:
    """Return (text, is_error) for one tool call."""
    if name == PLAN_TOOL:
        try:
            validate_task_plan(json.dumps(arguments), catalog)
        except ProposalValidationError as exc:
            errors = [issue.to_json() for issue in exc.issues]
            return (
                f"Rejected. Fix every error below and call {PLAN_TOOL} again with the "
                "complete plan.\n" + json.dumps(errors, ensure_ascii=False),
                True,
            )
        return ACCEPTED, False
    if name == DECISION_TOOL:
        well_formed = isinstance(arguments, dict) and set(arguments) == {"kind"}
        if not well_formed or arguments["kind"] not in ("continue", "finish"):
            return (
                f'Rejected. Call {DECISION_TOOL} with exactly {{"kind": "continue"}} or '
                '{"kind": "finish"}.',
                True,
            )
        return ACCEPTED, False
    return f"Unknown tool {name!r}.", True


def handle(message: dict, catalog: SkillCatalog) -> dict | None:
    """Answer one JSON-RPC message; notifications get no reply."""
    msg_id = message.get("id")
    if msg_id is None:
        return None
    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        result = {
            "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "graph-manager-submit", "version": "1"},
        }
    elif method == "tools/list":
        result = {"tools": tool_definitions(catalog)}
    elif method == "tools/call":
        text, is_error = call_tool(params.get("name"), params.get("arguments"), catalog)
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    elif method == "ping":
        result = {}
    else:
        error = {"code": -32601, "message": f"method not found: {method}"}
        return {"jsonrpc": "2.0", "id": msg_id, "error": error}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(stdin: TextIO, stdout: TextIO, catalog: SkillCatalog) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            reply = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "parse error"},
            }
        else:
            reply = handle(message, catalog) if isinstance(message, dict) else None
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Graph Manager submit tools (stdio MCP)")
    parser.add_argument("--zenobench-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    serve(sys.stdin, sys.stdout, ZenoBenchLibrary(args.zenobench_root).load())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
