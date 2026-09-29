"""Domain errors with stable codes and recruiter-readable messages (SYSTEM_DESIGN §6).

Adapters map these to responses: the JSON API uses `http_status` and `code`,
the HTML views show `message` (and `hint`) in a toast. Messages are shown verbatim.
"""

from typing import ClassVar


class DomainError(Exception):
    """Base class for every rule violation the recruiter can trigger."""

    code: ClassVar[str] = "DOMAIN_ERROR"
    http_status: ClassVar[int] = 400

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class FinalOutcomeError(DomainError):
    """Hired and Rejected are final; nothing can change them."""

    code = "FINAL_OUTCOME"
    http_status = 409


class StaleVersionError(DomainError):
    """The candidate changed after the caller loaded it (double click, second tab)."""

    code = "STALE_VERSION"
    http_status = 409


class NotFoundError(DomainError):
    """No candidate with that id."""

    code = "NOT_FOUND"
    http_status = 404


class InvalidInputError(DomainError):
    """Input breaks a domain rule (for example an empty or too-long note)."""

    code = "INVALID_INPUT"
    http_status = 400


class DuplicateEmailError(DomainError):
    """Another candidate already uses this email."""

    code = "DUPLICATE_EMAIL"
    http_status = 409
