"""Small interfaces between the application and its model, library, and environment adapters."""

from typing import Protocol

from .domain.env_types import (
    ContractCall,
    ExecutionReply,
    ExpStatus,
    GoalCheck,
    StartedTask,
    TaskRequest,
)
from .domain.models import ImageInput
from .domain.skills import SkillCatalog


class PlanningSessionPort(Protocol):
    """A runtime that retains conversation history between calls."""

    session_id: str

    def ask(self, text: str, images: tuple[ImageInput, ...] = ()) -> str:
        raise NotImplementedError


class SkillLibraryPort(Protocol):
    def load(self) -> SkillCatalog:
        raise NotImplementedError


class ModelPortError(RuntimeError):
    """A model request failed; a partial output may be repairable."""

    def __init__(self, message: str, partial_output: str | None = None):
        self.partial_output = partial_output
        super().__init__(message)


class EnvironmentPort(Protocol):
    """The ZenoBench environment service (interface v3); one exp_id is one simulator."""

    def initial_task(self, request: TaskRequest) -> StartedTask:
        raise NotImplementedError

    def do_contract(self, exp_id: str, calls: list[ContractCall]) -> ExecutionReply:
        raise NotImplementedError

    def check_task(self, exp_id: str) -> GoalCheck:
        raise NotImplementedError

    def observe(self, exp_id: str) -> ExpStatus:
        raise NotImplementedError


EXP_GONE_CODES = frozenset({"EXP_RELEASED", "SIM_CRASHED", "SIM_ERROR"})


class EnvironmentPortError(RuntimeError):
    """A request failed as a whole, so no contract-level result exists.

    error_code is the service's code (EXP_RELEASED, SIM_CRASHED, ...) or one raised on
    our side: CLIENT_TIMEOUT, TRANSPORT_ERROR, BAD_RESPONSE, HTTP_ERROR.
    """

    def __init__(self, message: str, *, error_code: str, http_status: int | None = None):
        self.error_code = error_code
        self.http_status = http_status
        super().__init__(message)

    @property
    def exp_gone(self) -> bool:
        """The service released the exp; only a new exp can continue the task."""
        return self.error_code in EXP_GONE_CODES

    @property
    def bad_request(self) -> bool:
        """The service refused the request itself (400): retrying the same request cannot help."""
        return self.http_status == 400
