"""DeepSeek Harness SDK session adapter.

Harness owns the session log and its derived model history. This adapter sends
only the new user turn; it never replays previous messages from Python.
"""

import base64
import json
import math
import os
import sys
import tempfile
import threading
import uuid
from pathlib import Path

from ..domain.models import ImageInput
from ..domain.submission import DECISION_TOOL_NAME, PLAN_TOOL_NAME, SERVER_NAME
from ..ports import ModelPortError

PLANNER_PATCH = Path(__file__).resolve().parents[1] / "harness_profile" / "cordis.patch.yml"
SKILLS_PATCH_NAME = "graph-manager-skills.patch.yml"
SUBMIT_PATCH_NAME = "graph-manager-submit.patch.yml"
SUBMIT_TOOL_NAMES = frozenset({PLAN_TOOL_NAME, DECISION_TOOL_NAME})


def skills_patch(skills_dir: Path) -> list[dict]:
    """Expose only the synced ZenoBench skills: Harness lists each name and description
    and loads a SKILL.md body when the model asks for it."""
    return [
        {
            "id": "skill-filesystem",
            "config": {
                "includeDefaultRoots": False,
                "watch": False,
                "customSkillDirs": [str(skills_dir)],
            },
        }
    ]


def submit_tools_patch(zenobench_root: Path) -> list[dict]:
    """Start the submit tool server (adapters/submit_tools.py) inside each Harness session.

    A patch adds a plugin through an insert list; this Python runs the server, so it sees
    the same graph_manager package and vendored skills."""
    return [
        {
            "insert": [
                {
                    "id": "mcp-graph-submit",
                    "name": "@deepseek-ai/dsh-mcp-client",
                    "config": {
                        "serverName": SERVER_NAME,
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [
                            "-m",
                            "graph_manager.adapters.submit_tools",
                            "--zenobench-root",
                            str(zenobench_root),
                        ],
                        "failOnStartupError": True,
                    },
                }
            ]
        }
    ]


def submitted_answer(events) -> str | None:
    """The arguments of the turn's last accepted submit call as JSON text.

    Without an accepted call, the last submitted arguments are returned so the caller's
    validator reports why they fail; None means the model submitted nothing.
    """
    calls: dict[object, object] = {}
    last = accepted = None
    for event in events:
        data = event.get("data") or {}
        if event.get("type") == "tool/call" and data.get("name") in SUBMIT_TOOL_NAMES:
            calls[data.get("callId")] = data.get("arguments")
            last = data.get("arguments")
        elif event.get("type") == "tool/result":
            for block in (data.get("message") or {}).get("content") or ():
                call_id = block.get("toolCallId")
                if block.get("type") == "tool-result" and call_id in calls:
                    if block.get("isError") is False:
                        accepted = calls[call_id]
    answer = accepted if accepted is not None else last
    if answer is None or isinstance(answer, str):
        return answer
    return json.dumps(answer)


def _load_harness_class():
    try:
        from deepseek_harness import DeepSeekHarness
    except ImportError as exc:
        raise RuntimeError("DeepSeek Harness SDK is required; run uv sync") from exc
    return DeepSeekHarness


class DeepSeekHarnessSession:
    def __init__(
        self,
        *,
        dsh_home: Path,
        model: str,
        cwd: Path,
        skills_dir: Path,
        provider: str = "deepseek-official",
        profile: str = "sdk",
        patches: tuple[Path, ...] = (),
        base_url: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        session_id: str | None = None,
        turn_timeout_seconds: float = 300,
    ):
        if not model.strip() or not provider.strip() or not profile.strip():
            raise ValueError("model, provider, and profile must be nonempty")
        if profile != "sdk":
            raise ValueError("only the verified sdk profile is supported")
        if max_tokens is not None and (type(max_tokens) is not int or max_tokens < 1):
            raise ValueError("max_tokens must be a positive integer")
        if session_id is not None and not session_id.strip():
            raise ValueError("session_id must be nonempty")
        if (
            isinstance(turn_timeout_seconds, bool)
            or not isinstance(turn_timeout_seconds, (int, float))
            or not math.isfinite(turn_timeout_seconds)
            or turn_timeout_seconds <= 0
        ):
            raise ValueError("turn_timeout_seconds must be a positive finite number")
        if turn_timeout_seconds > 86_400:
            raise ValueError("turn_timeout_seconds cannot exceed one day")
        self.dsh_home = Path(dsh_home).resolve()
        self.cwd = Path(cwd).resolve()
        self.skills_dir = Path(skills_dir).resolve()
        if not self.skills_dir.is_dir():
            raise ValueError(f"skills directory does not exist: {self.skills_dir}")
        self.skills_patch = self.dsh_home / SKILLS_PATCH_NAME
        self.submit_patch = self.dsh_home / SUBMIT_PATCH_NAME
        self.model = model
        self.provider = provider
        self.profile = profile
        self.patches = (str(PLANNER_PATCH), str(self.skills_patch), str(self.submit_patch)) + tuple(
            str(Path(patch).resolve()) for patch in patches
        )
        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.session_id = session_id or f"graph-plan-{uuid.uuid4().hex}"
        self.turn_timeout_seconds = turn_timeout_seconds
        self._harness = None
        self._session = None
        self._closed = False
        self._close_lock = threading.Lock()

    def __enter__(self) -> "DeepSeekHarnessSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    def close(self) -> None:
        with self._close_lock:
            self._closed = True
            harness = self._harness
            self._harness = None
            self._session = None
        if harness is not None:
            harness.close()

    def _write_patch(self, path: Path, entries: list[dict]) -> None:
        """Concurrent sessions share dsh_home, so replace a patch atomically: a Harness
        starting meanwhile reads either the old or the new file, never a half-written one."""
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(entries, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(body)
        try:
            os.replace(handle.name, path)
        except BaseException:
            Path(handle.name).unlink(missing_ok=True)
            raise

    def ask(self, text: str, images: tuple[ImageInput, ...] = ()) -> str:
        if self._closed:
            raise RuntimeError("Harness session is closed")
        if not text.strip():
            raise ValueError("Harness prompt must be nonempty")
        if self._session is None:
            self._write_patch(self.skills_patch, skills_patch(self.skills_dir))
            self._write_patch(self.submit_patch, submit_tools_patch(self.skills_dir.parent))
            harness_class = _load_harness_class()
            self._harness = harness_class(
                dsh_home=str(self.dsh_home),
                cwd=str(self.cwd),
                provider=self.provider,
                model=self.model,
                profile=self.profile,
                patches=self.patches,
                base_url=self.base_url,
                api_key=self.api_key,
                max_tokens=self.max_tokens,
            )
            try:
                self._session = self._harness.start_session(self.session_id)
            except Exception:
                self.close()
                raise
        content: str | list[dict] = text
        if images:
            content = [{"type": "text", "text": text}] + [
                {
                    "type": "image",
                    "data": base64.b64encode(image.data).decode("ascii"),
                    "mimeType": image.mime,
                }
                for image in images
            ]
        runtime_session = self._session
        timed_out = threading.Event()
        turn_lock = threading.Lock()
        active = True

        def expire_turn() -> None:
            nonlocal active
            with turn_lock:
                if not active:
                    return
                active = False
                timed_out.set()
            self.close()

        timer = threading.Timer(self.turn_timeout_seconds, expire_turn)
        timer.daemon = True
        timer.start()
        try:
            result = runtime_session.run(content)
        except Exception as exc:
            if timed_out.is_set():
                raise ModelPortError(
                    f"Harness turn timed out after {self.turn_timeout_seconds:g} seconds"
                ) from exc
            raise
        finally:
            with turn_lock:
                active = False
            timer.cancel()
        if timed_out.is_set():
            raise ModelPortError(
                f"Harness turn timed out after {self.turn_timeout_seconds:g} seconds"
            )
        answer = submitted_answer(getattr(result, "events", None) or ())
        if answer is not None:
            return answer
        raw_text = result.final_response
        if result.finish_reason != "completed":
            raise ModelPortError(
                f"Harness turn ended with finish_reason={result.finish_reason}",
                partial_output=raw_text or None,
            )
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ModelPortError("Harness returned no assistant text")
        return raw_text
