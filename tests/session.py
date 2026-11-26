"""HTTP session for tests that supply their own service credentials."""

import requests
from requests.auth import AuthBase


class _ExplicitAuthOnly(AuthBase):
    """Use the request's existing headers when no auth handler is supplied."""

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Preserve the request's explicit authentication headers.

        Args:
            request: Prepared request.

        Returns:
            requests.PreparedRequest: The same request with its headers unchanged.
        """
        return request


class ApiSession(requests.Session):
    """Keep Requests environment settings for TLS and proxies while ignoring netrc."""

    def __init__(self) -> None:
        """Set a fallback auth handler to prevent Requests from consulting netrc."""
        super().__init__()
        self.auth = _ExplicitAuthOnly()

    def rebuild_auth(self, prepared_request: requests.PreparedRequest, response: requests.Response) -> None:
        """Apply Requests' redirect stripping policy without loading target credentials.

        Args:
            prepared_request: Request prepared for the redirect target.
            response: Redirect response from the previous request.
        """
        if self.should_strip_auth(response.request.url, prepared_request.url):
            prepared_request.headers.pop('Authorization', None)
