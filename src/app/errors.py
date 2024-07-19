"""Custom exceptions."""

from starlette.status import HTTP_400_BAD_REQUEST


class ClientError(Exception):
    """Error that should be returned to the client."""

    def __init__(self, *args, **kwargs):
        """Initialize ClientError with `status_code`."""
        self.status_code = kwargs.pop("status_code", HTTP_400_BAD_REQUEST)
        super().__init__(*args, **kwargs)


class CircuitError(ClientError):
    """Circuit error that should be returned to the client."""
