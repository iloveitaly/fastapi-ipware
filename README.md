[![Release Notes](https://img.shields.io/github/release/iloveitaly/fastapi-ipware)](https://github.com/iloveitaly/fastapi-ipware/releases)
[![Downloads](https://static.pepy.tech/badge/fastapi-ipware/month)](https://pepy.tech/project/fastapi-ipware)
![GitHub CI Status](https://github.com/iloveitaly/fastapi-ipware/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# fastapi-ipware

A FastAPI/Starlette-native wrapper for [python-ipware](https://github.com/un33k/python-ipware) that eliminates the need for WSGI-style header conversion.

`python-ipware` expects WSGI-style headers (`HTTP_X_FORWARDED_FOR`), but FastAPI uses natural header names (`X-Forwarded-For`). This wrapper handles the conversion automatically so you don't have to.

Also, the default precedence order is optimized for modern cloud deployments. See the [default precedence configuration](https://github.com/iloveitaly/fastapi-ipware/blob/main/fastapi_ipware/__init__.py#L48-L58) in the source code. This is different from the
default ordering ipware which deprioritizes platform-specific headers, which is often the wrong ordering if you are using something like CloudFlare.

## Features

- **Zero conversion overhead** - Headers converted once at initialization, not on every request
- **FastAPI-native API** - Works directly with FastAPI/Starlette `Request` objects
- **Customizable precedence** - Easy to configure header priority for your infrastructure
- **Proxy validation** - Supports trusted proxy lists and proxy count validation

## Installation

```bash
uv add fastapi-ipware
```

## Quick Start

`trusted` is true only when the request came through the proxies configured with `proxy_count` or `proxy_list`.

`proxy_count=N` returns the address just left of the N rightmost proxies, instead of the first public address, and rejects a shorter chain. `X-Forwarded-For: 203.0.113.10, 10.0.0.1, 10.0.0.2` returns `203.0.113.10` with no `proxy_count`, and `10.0.0.1` with `proxy_count=1`.

### Using FastAPI Dependency Injection

```python
from typing import Annotated
from fastapi import Depends, FastAPI
from fastapi_ipware import ClientIpResult, FastAPIIpWare

app = FastAPI()
ipware = FastAPIIpWare()


@app.get("/")
async def get_ip(client: Annotated[ClientIpResult, Depends(ipware)]):
    ip, trusted = client
    return {
        "ip": str(ip) if ip else None,
        "trusted": trusted,
        "is_public": ip.is_global if ip else None,
    }


# Or inject only the IP object or string directly:
@app.get("/ip-string")
async def get_ip_string(ip_str: Annotated[str | None, Depends(ipware.get_ip_str)]):
    return {"ip": ip_str}
```

### Using Request Directly

```python
from fastapi import FastAPI, Request
from fastapi_ipware import FastAPIIpWare

app = FastAPI()
ipware = FastAPIIpWare()


@app.get("/")
async def get_ip(request: Request):
    ip, trusted = ipware.get_client_ip_from_request(request)
    return {"ip": str(ip) if ip else None, "trusted": trusted}
```

### Using ASGI Middleware

Automatically extract the client IP onto `request.state` for every request:

```python
from fastapi import FastAPI, Request
from fastapi_ipware import IpWareMiddleware

app = FastAPI()
app.add_middleware(IpWareMiddleware)


@app.get("/")
async def get_ip(request: Request):
    return {
        "ip": request.state.client_ip_str,
        "trusted": request.state.ip_trusted,
    }
```

Pass a configured resolver when you need one. Omit `strict` to use that resolver's `default_strict`; pass `strict=` to override it.

```python
from fastapi_ipware import FastAPIIpWare, IpWareMiddleware

ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
app.add_middleware(IpWareMiddleware, ipware=ipware)
```

### Custom Header Precedence

Customize which headers are checked and in what order:

```python
# Prioritize Cloudflare headers
ipware = FastAPIIpWare(
    precedence=(
        "CF-Connecting-IP",
        "X-Forwarded-For",
        "X-Real-IP",
    )
)

# NGINX configuration
ipware = FastAPIIpWare(
    precedence=(
        "X-Real-IP",
        "X-Forwarded-For",
    )
)
```

### Proxy Count Validation

Validate that requests pass through the expected number of proxies:

```python
# Expect exactly 1 proxy (e.g., AWS ALB).
# default_strict applies to Depends(ipware), dependency(), and IpWareMiddleware.
ipware = FastAPIIpWare(proxy_count=1, default_strict=True)

# In strict mode, must be exactly 1 proxy
ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

# In non-strict mode, allow 1 or more proxies
ip, trusted = ipware.get_client_ip_from_request(request, strict=False)
```

### Trusted Proxy List

Validate that requests pass through specific trusted proxies (supports IP prefixes, exact IPs, and CIDR networks):

```python
# Trust specific proxy IP prefixes or CIDR networks
ipware = FastAPIIpWare(
    proxy_list=["10.0.", "10.1.", "100.64.0.0/10"]  # AWS internal IPs and CGNAT CIDR
)

ip, trusted = ipware.get_client_ip_from_request(request)

# trusted=True only if request came through specified proxies
```

### Combined Validation

Use both proxy count and trusted proxy list:

```python
# Expect 1 proxy from a specific IP range
ipware = FastAPIIpWare(proxy_count=1, proxy_list=["10.0."])
```

### Algorithm Engine Selection

Choose between python-ipware 4.x engines (`auto` / `modern` / `legacy`):

```python
# Modern engine (default): enhanced header parsing and RFC 7239 support
ipware = FastAPIIpWare(algorithm="modern")

# Legacy engine: frozen byte-for-byte v3 behavior
ipware = FastAPIIpWare(algorithm="legacy")
```

## IP Address Types

The returned IP address object has useful properties:

```python
ip, _ = ipware.get_client_ip_from_request(request)

if ip:
    print(f"Is public: {ip.is_global}")
    print(f"Is private: {ip.is_private}")
    print(f"Is loopback: {ip.is_loopback}")
    print(f"Is multicast: {ip.is_multicast}")
```

python-ipware automatically prefers:

1. Public (global) IPs first
2. Private IPs second
3. Loopback IPs last

## License

[MIT License](LICENSE.md)

## Credits

- Built on top of [python-ipware](https://github.com/un33k/python-ipware) by un33k.
- https://github.com/long2ice/fastapi-limiter/blob/8d179c058fa2aaf98f3450c9026a7300ae2b3bdd/fastapi_limiter/__init__.py#L11

---

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
