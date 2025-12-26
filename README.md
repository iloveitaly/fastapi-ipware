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

[Take a look at this example usage.](https://github.com/iloveitaly/structlog-config/blob/1e32f7afd206485b1356b322596cc19cb0bef8ba/structlog_config/fastapi_access_logger.py#L57-L72)

```python
from fastapi import FastAPI, Request
from fastapi_ipware import FastAPIIpWare

app = FastAPI()
ipware = FastAPIIpWare()

@app.get("/")
async def get_ip(request: Request):
    ip, trusted = ipware.get_client_ip_from_request(request)
    
    if ip:
        return {
            "ip": str(ip),
            "trusted": trusted,
            "is_public": ip.is_global,
            "is_private": ip.is_private,
        }
    
    return {"error": "Could not determine IP"}
```

## Usage

### Basic Usage

```python
from fastapi_ipware import FastAPIIpWare

# Use default configuration (optimized for FastAPI/cloud deployments)
ipware = FastAPIIpWare()

ip, trusted = ipware.get_client_ip_from_request(request)
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
# Expect exactly 1 proxy (e.g., AWS ALB)
ipware = FastAPIIpWare(proxy_count=1)

# In strict mode, must be exactly 1 proxy
ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

# In non-strict mode, allow 1 or more proxies
ip, trusted = ipware.get_client_ip_from_request(request, strict=False)
```

### Trusted Proxy List

Validate that requests pass through specific trusted proxies:

```python
# Trust specific proxy IP prefixes
ipware = FastAPIIpWare(
    proxy_list=["10.0.", "10.1."]  # AWS internal IPs
)

ip, trusted = ipware.get_client_ip_from_request(request)

# trusted=True only if request came through specified proxies
```

### Combined Validation

Use both proxy count and trusted proxy list:

```python
# Expect 1 proxy from a specific IP range
ipware = FastAPIIpWare(
    proxy_count=1,
    proxy_list=["10.0."]
)
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
