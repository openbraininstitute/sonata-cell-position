"""Custom exceptions."""


class ClientError(Exception):
    """Error that should be returned to the client."""


class CircuitError(ClientError):
    """Circuit error that should be returned to the client."""
