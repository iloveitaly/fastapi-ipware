from typing import List, Optional, Tuple, Union
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
        precedence: Optional[Tuple[str, ...]] = None,
        leftmost: bool = True,
        proxy_count: Optional[int] = None,
        proxy_list: Optional[List[str]] = None,
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
                       Used to validate the request came through trusted proxies.
        """
        # FastAPI-native precedence using actual header names with dashes
        if precedence is None:
            precedence = (
                "X-Forwarded-For",  # Most common, used by AWS ELB, nginx, etc.
                "X-Real-IP",  # NGINX
                "CF-Connecting-IP",  # Cloudflare
                "True-Client-IP",  # Cloudflare Enterprise
                "Fastly-Client-IP",  # Fastly, Firebase
                "X-Client-IP",  # Microsoft Azure
                "X-Cluster-Client-IP",  # Rackspace Cloud Load Balancers
                "Forwarded-For",  # RFC 7239
                "Forwarded",  # RFC 7239
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
    ) -> Tuple[Union[ipaddress.IPv4Address, ipaddress.IPv6Address, None], bool]:
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

        return self.get_client_ip(meta, strict=strict)


__all__ = ["FastAPIIpWare"]
