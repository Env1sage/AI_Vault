import pytest
from vault_shared.errors import (
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    VaultError,
)


@pytest.mark.parametrize(
    ("error_cls", "expected_status", "expected_code"),
    [
        (VaultError, 500, "internal_error"),
        (NotFoundError, 404, "not_found"),
        (ValidationError, 422, "validation_error"),
        (UnauthorizedError, 401, "unauthorized"),
        (ConflictError, 409, "conflict"),
        (DependencyUnavailableError, 503, "dependency_unavailable"),
    ],
)
def test_each_typed_error_carries_its_http_status_and_code(error_cls, expected_status, expected_code) -> None:
    error = error_cls("something went wrong", details={"field": "value"})

    assert error.http_status == expected_status
    assert error.code == expected_code
    assert error.message == "something went wrong"
    assert error.details == {"field": "value"}


def test_details_default_to_empty_dict_when_omitted() -> None:
    error = NotFoundError("missing")

    assert error.details == {}
