"""HTTP client for the ZenoBench environment service (interface v3)."""

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from ..domain.env_types import (
    ContractCall,
    ExecutionReply,
    ExpStatus,
    GoalCheck,
    StartedTask,
    TaskRequest,
)
from ..ports import EnvironmentPortError

# Client timeouts in seconds, from interface v3. initial_task includes waiting for an earlier
# simulator to start.
TIMEOUTS = {"initial_task": 15 * 60, "do_contract": 30 * 60, "check_task": 30 * 60, "observe": 60}


def _service_error(endpoint: str, exc: urllib.error.HTTPError) -> EnvironmentPortError:
    try:
        body = json.loads(exc.read())
        code, message = body["error_code"], body["error"]
    except (ValueError, KeyError, TypeError, AttributeError):
        code, message = "HTTP_ERROR", str(exc.reason)
    return EnvironmentPortError(
        f"{endpoint}: HTTP {exc.code} {code}: {message}", error_code=code, http_status=exc.code
    )


class HttpEnvironment:
    def __init__(
        self,
        base_url: str,
        *,
        urlopen: Callable = urllib.request.urlopen,
        timeouts: dict[str, float] | None = None,
    ):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("environment URL must start with http:// or https://")
        self.base_url = base_url.rstrip("/")
        self._urlopen = urlopen
        self.timeouts = {**TIMEOUTS, **(timeouts or {})}

    def initial_task(self, request: TaskRequest) -> StartedTask:
        return self._call("initial_task", request.to_json(), StartedTask.from_json)

    def do_contract(self, exp_id: str, calls: list[ContractCall]) -> ExecutionReply:
        if not calls:
            raise ValueError("calls must be nonempty")
        body = {"exp_id": exp_id, "calls": [call.to_json() for call in calls]}
        return self._call("do_contract", body, ExecutionReply.from_json)

    def check_task(self, exp_id: str) -> GoalCheck:
        return self._call("check_task", {"exp_id": exp_id}, GoalCheck.from_json)

    def observe(self, exp_id: str) -> ExpStatus:
        return self._call("observe", {"exp_id": exp_id}, ExpStatus.from_json)

    def _call(self, endpoint: str, body: dict, parse: Callable):
        data = self._post(endpoint, body)
        try:
            return parse(data)
        except ValueError as exc:
            raise EnvironmentPortError(
                f"{endpoint} returned an unexpected reply: {exc}", error_code="BAD_RESPONSE"
            ) from exc

    def _post(self, endpoint: str, body: dict) -> dict:
        timeout = self.timeouts[endpoint]
        request = urllib.request.Request(
            f"{self.base_url}/{endpoint}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise _service_error(endpoint, exc) from exc
        except TimeoutError as exc:
            raise self._timeout(endpoint, timeout) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise self._timeout(endpoint, timeout) from exc
            raise EnvironmentPortError(
                f"{endpoint} failed: {exc.reason}", error_code="TRANSPORT_ERROR"
            ) from exc
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise EnvironmentPortError(
                f"{endpoint} returned invalid JSON: {exc}", error_code="BAD_RESPONSE"
            ) from exc
        if not isinstance(data, dict):
            raise EnvironmentPortError(
                f"{endpoint} returned {type(data).__name__}, not an object",
                error_code="BAD_RESPONSE",
            )
        return data

    @staticmethod
    def _timeout(endpoint: str, timeout: float) -> EnvironmentPortError:
        return EnvironmentPortError(
            f"{endpoint} got no reply within {timeout:g} s", error_code="CLIENT_TIMEOUT"
        )
