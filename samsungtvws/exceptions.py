class ConnectionFailure(Exception):
    """Error during connection."""
    pass

class HttpApiError(Exception):
    """Error using HTTP API."""
    pass