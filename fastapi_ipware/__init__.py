import ipaddress

from python_ipware.python_ipware import IpWare  # type: ignore[import-not-found]
from starlette.requests import Request


class FastAPIIpWare(IpWare):
    """
    A FastAPI/Starlette-native wrapper around python-ipware that eliminates
    the need for WSGI-style header conversion at request time.

    This class accepts natural header names (e.g., "X-Forwarded-For") and
    handles the conversion to ipware's expected format internally.

    Example:
        >>> from fastapi_ipware import FastAPIIpWare
        >>> ipware = FastAPIIpWare()
        >>> ip, trusted = ipware.get_client_ip_from_request(request)

        >>> # With custom precedence
        >>> ipware = FastAPIIpWare(
        ...     precedence=("CF-Connecting-IP", "X-Forwarded-For"),
        ...     proxy_count=1
        ... )
    """

    def __init__(
        self,
        precedence: tuple[str, ...] | None = None,
        leftmost: bool = True,
        proxy_count: int | None = None,
        proxy_list: list[str] | None = None,
    ):
        """
        Initialize FastAPIIpWare with optional configuration.

        Args:
            precedence: Tuple of header names to check in order. Uses natural header
                       names with dashes (e.g., "X-Forwarded-For", "X-Real-IP").
                       If None, uses FastAPI-optimized defaults.
            leftmost: If True, use leftmost IP in comma-separated list (standard).
                     If False, use rightmost IP (rare legacy configurations).
            proxy_count: Expected number of proxies between client and server.
                        Used to validate and extract the correct client IP.
            proxy_list: List of trusted proxy IP prefixes (e.g., ["10.1.", "10.2.3"]).
        """
        # Header precedence order: Provider-specific headers before generic ones
        #
        # We prioritize provider-specific headers (CF-Connecting-IP, True-Client-IP, etc.)
        # over generic headers (X-Forwarded-For, X-Real-IP) because:
        #   1. Provider headers are set by trusted CDN/proxy infrastructure
        #   2. They cannot be spoofed by clients
        #   3. They represent the most reliable source of client IP information
        #
        # Generic headers like X-Forwarded-For can be set by anyone and are easier
        # to manipulate, so they should only be used as fallbacks.
        if precedence is None:
            precedence = (
                # Provider-specific headers (highest reliability)
                "CF-Connecting-IP",  # Cloudflare
                "True-Client-IP",  # Cloudflare Enterprise
                "Fastly-Client-IP",  # Fastly, Firebase
                "X-Client-IP",  # Microsoft Azure
                "X-Cluster-Client-IP",  # Rackspace Cloud Load Balancers
                # Generic headers (fallback)
                "X-Forwarded-For",  # Generic, used by AWS ELB, nginx, etc.
                "X-Real-IP",  # NGINX
                # NOTE: Upstream python-ipware treats Forwarded headers as plain IP lists.
                # RFC 7239 `Forwarded` parameters (for=) are not parsed.
                "Forwarded-For",  # RFC 7239 (plain IP list only)
                "Forwarded",  # RFC 7239 (plain IP list only)
                "Client-IP",  # Akamai, Cloudflare
            )

        # Store FastAPI-style precedence for reference
        self._fastapi_precedence = precedence

        # Convert user-friendly header names (with dashes) to WSGI format once
        # This happens only at initialization, not on every request
        wsgi_precedence = tuple(
            f"HTTP_{header.upper().replace('-', '_')}" for header in precedence
        )

        # Initialize parent class with WSGI-style headers
        super().__init__(wsgi_precedence, leftmost, proxy_count, proxy_list)

    def get_client_ip_from_request(
        self, request: Request, strict: bool = False
    ) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address | None, bool]:
        """
        Get client IP address from a FastAPI/Starlette Request object.

        This is the main method you should use with FastAPI/Starlette applications.
        It handles the header conversion automatically.

        Args:
            request: FastAPI/Starlette Request object
            strict: If True, enforce exact proxy count/list match.
                   If False, allow more proxies than specified.

        Returns:
            Tuple of (ip_address, trusted_route) where:
                - ip_address: IPv4Address or IPv6Address object (or None if not found)
                - trusted_route: True if request came through trusted proxies, False otherwise

        Example:
            >>> ip, trusted = ipware.get_client_ip_from_request(request)
            >>> if ip:
            ...     print(f"Client IP: {ip}")
            ...     print(f"Is global: {ip.is_global}")
            ...     print(f"Is private: {ip.is_private}")
        """
        # Convert Starlette headers to WSGI-style dict that parent class expects
        # This happens once per request
        meta = {
            f"HTTP_{name.upper().replace('-', '_')}": value
            for name, value in request.headers.items()
        }

        if request.client:
            # NOTE: python-ipware falls back to REMOTE_ADDR when no headers match.
            # Map Starlette's connection info to that expected key.
            meta["REMOTE_ADDR"] = request.client.host

        return self.get_client_ip(meta, strict=strict)


__all__ = ["FastAPIIpWare"]
