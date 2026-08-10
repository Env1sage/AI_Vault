class VaultError(Exception):
    """Base class for every typed error raised by domain/application code.

    Per Engineering Handbook §26: domain and application layers raise these,
    never raw strings or provider-specific exceptions. Only the presentation
    layer (FastAPI exception handlers) translates one of these into an HTTP
    response shape.
    """

    http_status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(VaultError):
    http_status = 404
    code = "not_found"


class ValidationError(VaultError):
    http_status = 422
    code = "validation_error"


class UnauthorizedError(VaultError):
    """Not authenticated — missing, invalid, or expired credentials."""

    http_status = 401
    code = "unauthorized"


class ForbiddenError(VaultError):
    """Authenticated, but the identified user's role doesn't permit this
    action — distinct from UnauthorizedError (Handbook §13.1: Authentication
    vs. Authorization are different layers)."""

    http_status = 403
    code = "forbidden"


class ConflictError(VaultError):
    http_status = 409
    code = "conflict"


class RateLimitExceededError(VaultError):
    http_status = 429
    code = "rate_limit_exceeded"


class DependencyUnavailableError(VaultError):
    """Raised when a required infrastructure dependency (database, queue,
    external API) cannot be reached — distinct from a domain-level error."""

    http_status = 503
    code = "dependency_unavailable"
