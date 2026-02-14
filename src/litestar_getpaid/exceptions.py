"""Exception handling for litestar-getpaid."""

from getpaid_core.exceptions import (
    CommunicationError,
    CredentialsError,
    GetPaidException,
    InvalidCallbackError,
    InvalidTransitionError,
)
from litestar import Request, Response


class PaymentNotFoundError(Exception):
    """Payment with given ID was not found."""

    def __init__(self, payment_id: str) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id!r} not found")


class ConfigurationError(Exception):
    """A required component is not configured."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def _error_response(
    request: Request, detail: str, code: str, status_code: int
) -> Response:
    return Response(
        content={"detail": detail, "code": code},
        status_code=status_code,
    )


def handle_communication_error(
    request: Request, exc: CommunicationError
) -> Response:
    """Map CommunicationError to 502."""
    return _error_response(request, str(exc), "communication_error", 502)


def handle_invalid_callback(
    request: Request, exc: InvalidCallbackError
) -> Response:
    """Map InvalidCallbackError to 400."""
    return _error_response(request, str(exc), "invalid_callback", 400)


def handle_invalid_transition(
    request: Request, exc: InvalidTransitionError
) -> Response:
    """Map InvalidTransitionError to 409."""
    return _error_response(request, str(exc), "invalid_transition", 409)


def handle_credentials_error(
    request: Request, exc: CredentialsError
) -> Response:
    """Map CredentialsError to 500."""
    return _error_response(request, str(exc), "credentials_error", 500)


def handle_payment_not_found(
    request: Request, exc: PaymentNotFoundError
) -> Response:
    """Map PaymentNotFoundError to 404."""
    return _error_response(request, str(exc), "not_found", 404)


def handle_getpaid_exception(
    request: Request, exc: GetPaidException
) -> Response:
    """Map generic GetPaidException to 400."""
    return _error_response(request, str(exc), "payment_error", 400)


def handle_configuration_error(
    request: Request, exc: ConfigurationError
) -> Response:
    """Map ConfigurationError to 500."""
    return _error_response(request, str(exc), "configuration_error", 500)


EXCEPTION_HANDLERS = {
    CommunicationError: handle_communication_error,
    InvalidCallbackError: handle_invalid_callback,
    InvalidTransitionError: handle_invalid_transition,
    CredentialsError: handle_credentials_error,
    PaymentNotFoundError: handle_payment_not_found,
    ConfigurationError: handle_configuration_error,
    GetPaidException: handle_getpaid_exception,
}
