"""Domain errors. Services raise these; main.py maps them to the JSON error envelope."""
from typing import Any


class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


class NotFound(DomainError):
    status_code = 404
    code = "not_found"


class Conflict(DomainError):
    status_code = 409
    code = "conflict"


class Unauthorized(DomainError):
    status_code = 401
    code = "unauthorized"


class Forbidden(DomainError):
    status_code = 403
    code = "forbidden"


class ValidationFailed(DomainError):
    status_code = 422
    code = "validation_error"


class ServiceUnavailable(DomainError):
    status_code = 503
    code = "service_unavailable"
