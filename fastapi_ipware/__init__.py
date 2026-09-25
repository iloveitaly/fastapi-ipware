import ipaddress
from collections.abc import Callable
from typing import Literal

from python_ipware import IpWare
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from .version import __version__

Algorithm = Literal["auto", "modern", "legacy"]
IpAddressType = ipaddress.IPv4Address | ipaddress.IPv6Address
ClientIpResult = tuple[IpAddressType | None, bool]

DEFAULT_PRECEDENCE: tuple[str, ...] = (
    # Provider-specific headers (highest reliability)
    "CF-Connecting-IP",  # Cloudflare
    "True-Client-IP",  # Cloudflare Enterprise, Akamai
    "Fastly-Client-IP",  # Fastly, Firebase
    "Fly-Client-IP",  # Fly.io
    "X-Client-IP",  # Microsoft Azure
    "X-Azure-ClientIP",  # Azure Front Door
    "DO-Connecting-IP",  # DigitalOcean App Platform
    "X-Cluster-Client-IP",  # Rackspace Cloud Load Balancers
    "X-Appengine-User-IP",  # Google App Engine
    "X-Envoy-External-Address",  # Envoy / Istio
    # Generic headers (fallback)
    "X-Forwarded-For",  # Generic, used by AWS ELB, nginx, etc.
    "X-Real-IP",  # NGINX
    "Forwarded-For",  # Plain IP list variant
    "Forwarded",  # RFC 7239 (for=...;proto=...)
    "Client-IP",  # Akamai, Cloudflare fallback
    "REMOTE_ADDR",  # Direct connection fallback
)


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

        >>> # Direct FastAPI route dependency
        >>> @app.get("/")
        ... def endpoint(client: ClientIpResult = Depends(ipware)):
        ...     ip, trusted = client
    """

    def __init__(
        self,
        precedence: tuple[str, ...] | None = None,
        leftmost: bool = True,
        proxy_count: int | None = None,
        proxy_list: list[str] | None = None,
        algorithm: Algorithm = "auto",
        default_strict: bool = False,
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
            proxy_list: List of trusted proxy IP prefixes, complete IPs, or CIDR networks
                       (e.g., ["10.1.", "198.84.193.157", "100.64.0.0/10"]).
            algorithm: Algorithm engine to use: "auto" (default, uses modern),
                      "modern" (v4 enhanced engine), or "legacy" (frozen v3 engine).
            default_strict: Used whenever strict is omitted: Depends(self),
                           dependency() with no argument, IpWareMiddleware, and
                           get_client_ip_from_request.
        """
        if precedence is None:
            precedence = DEFAULT_PRECEDENCE

        # Store FastAPI-style precedence for reference
        self._fastapi_precedence = precedence
        self.default_strict = default_strict

        # Expand precedence to support both natural and WSGI formats
        expanded_precedence: list[str] = []
        for header in precedence:
            if header == "REMOTE_ADDR":
                if "REMOTE_ADDR" not in expanded_precedence:
                    expanded_precedence.append("REMOTE_ADDR")
            elif header.startswith("HTTP_"):
                if header not in expanded_precedence:
                    expanded_precedence.append(header)
                non_http = header[5:].replace("_", "-")
                if non_http not in expanded_precedence:
                    expanded_precedence.append(non_http)
            else:
                if header not in expanded_precedence:
                    expanded_precedence.append(header)
                wsgi_form = f"HTTP_{header.upper().replace('-', '_')}"
                if wsgi_form not in expanded_precedence:
                    expanded_precedence.append(wsgi_form)

        super().__init__(
            tuple(expanded_precedence),
            leftmost=leftmost,
            proxy_count=proxy_count,
            proxy_list=proxy_list,
            algorithm=algorithm,
        )

    @property
    def precedence(self) -> tuple[str, ...]:
        """Header precedence tuple from the active engine."""
        return getattr(self.engine, "precedence", ())

    @property
    def leftmost(self) -> bool:
        """Leftmost setting from the active engine."""
        return getattr(self.engine, "leftmost", True)

    @property
    def proxy_count(self) -> int | None:
        """Proxy count setting from the active engine."""
        return getattr(self.engine, "proxy_count", None)

    @property
    def proxy_list(self) -> list[str]:
        """Proxy list setting from the active engine."""
        return getattr(self.engine, "proxy_list", [])

    def __call__(self, request: HTTPConnection) -> ClientIpResult:
        """FastAPI route dependency injection entrypoint."""
        return self.get_client_ip_from_request(request, strict=self.default_strict)

    def dependency(
        self, strict: bool | None = None
    ) -> Callable[[HTTPConnection], ClientIpResult]:
        """Return a FastAPI dependency. An omitted strict flag uses default_strict."""

        def _dep(request: HTTPConnection) -> ClientIpResult:
            return self.get_client_ip_from_request(request, strict=strict)

        return _dep

    def get_ip(self, request: HTTPConnection) -> IpAddressType | None:
        """Return only the client IP address (or None if unresolvable)."""
        ip, _ = self.get_client_ip_from_request(request, strict=self.default_strict)
        return ip

    def get_ip_str(self, request: HTTPConnection) -> str | None:
        """Return the client IP address as a string (or None if unresolvable)."""
        ip = self.get_ip(request)
        return str(ip) if ip is not None else None

    def get_client_ip_from_request(
        self, request: HTTPConnection, strict: bool | None = None
    ) -> ClientIpResult:
        """
        Get client IP address from a FastAPI/Starlette Request or WebSocket connection.

        Args:
            request: FastAPI/Starlette Request or HTTPConnection object
            strict: If True, enforce exact proxy count/list match.
                   If False, allow more proxies than specified.
                   If None, use self.default_strict.

        Returns:
            Tuple of (ip_address, trusted_route) where:
                - ip_address: IPv4Address or IPv6Address object (or None if not found)
                - trusted_route: True if request came through trusted proxies, False otherwise
        """
        if strict is None:
            strict = self.default_strict

        # Populate both WSGI-style headers and original Starlette headers
        meta = {
            f"HTTP_{name.upper().replace('-', '_')}": value
            for name, value in request.headers.items()
        }
        for name, value in request.headers.items():
            meta[name] = value

        if request.client:
            # Map Starlette's connection info to REMOTE_ADDR fallback
            meta["REMOTE_ADDR"] = request.client.host

        return self.get_client_ip(meta, strict=strict)


class IpWareMiddleware:
    """
    ASGI middleware that resolves the client IP address and attaches it to request state:
      - `request.state.client_ip`: IPv4Address | IPv6Address | None
      - `request.state.ip_trusted`: bool
      - `request.state.client_ip_str`: str | None

    Pass `ipware` to use a configured resolver. `strict` overrides that
    resolver's `default_strict`; omit it to use `default_strict`.
    """

    def __init__(
        self,
        app: ASGIApp,
        ipware: FastAPIIpWare | None = None,
        strict: bool | None = None,
    ) -> None:
        self.app = app
        self.ipware = ipware if ipware is not None else FastAPIIpWare()
        self.strict = strict

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            conn = HTTPConnection(scope)
            ip, trusted = self.ipware.get_client_ip_from_request(
                conn, strict=self.strict
            )
            scope.setdefault("state", {})
            scope["state"]["client_ip"] = ip
            scope["state"]["ip_trusted"] = trusted
            scope["state"]["client_ip_str"] = str(ip) if ip is not None else None

        await self.app(scope, receive, send)


__all__ = [
    "DEFAULT_PRECEDENCE",
    "Algorithm",
    "ClientIpResult",
    "FastAPIIpWare",
    "IpAddressType",
    "IpWareMiddleware",
    "__version__",
]
