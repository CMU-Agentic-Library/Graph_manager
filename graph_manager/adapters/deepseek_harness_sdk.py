"""DeepSeek Harness SDK session adapter.

Harness owns the session log and its derived model history. This adapter sends
only the new user turn; it never replays previous messages from Python.
"""

import base64
import json
import math
import threading
import uuid
from pathlib import Path

from ..ports import ModelPortError

PLANNER_PATCH = Path(__file__).resolve().parents[1] / "harness_profile" / "cordis.patch.yml"
SKILLS_PATCH_NAME = "graph-manager-skills.patch.yml"


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
        self.model = model
        self.provider = provider
        self.profile = profile
        self.patches = (str(PLANNER_PATCH), str(self.skills_patch)) + tuple(
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

    def ask(self, text: str, image: bytes | None = None, image_mime: str = "image/jpeg") -> str:
        if self._closed:
            raise RuntimeError("Harness session is closed")
        if not text.strip():
            raise ValueError("Harness prompt must be nonempty")
        if self._session is None:
            self.skills_patch.parent.mkdir(parents=True, exist_ok=True)
            self.skills_patch.write_text(
                json.dumps(skills_patch(self.skills_dir), indent=2) + "\n", encoding="utf-8"
            )
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
        if image is not None:
            content = [
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "data": base64.b64encode(image).decode("ascii"),
                    "mimeType": image_mime,
                },
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
        raw_text = result.final_response
        if result.finish_reason != "completed":
            raise ModelPortError(
                f"Harness turn ended with finish_reason={result.finish_reason}",
                partial_output=raw_text or None,
            )
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ModelPortError("Harness returned no assistant text")
        return raw_text
