# fastapi-ipware

A FastAPI/Starlette-native wrapper for [python-ipware](https://github.com/un33k/python-ipware) that eliminates the need for WSGI-style header conversion.

## Features

- **Zero conversion overhead** - Headers converted once at initialization, not on every request
- **FastAPI-native API** - Works directly with FastAPI/Starlette `Request` objects
- **Customizable precedence** - Easy to configure header priority for your infrastructure
- **Proxy validation** - Supports trusted proxy lists and proxy count validation
- **Thin wrapper** - Leverages all the battle-tested logic from python-ipware

## Installation

```bash
pip install fastapi-ipware
```

Or with uv:

```bash
uv add fastapi-ipware
```

## Quick Start

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

## Real-World Examples

### AWS Application Load Balancer

```python
ipware = FastAPIIpWare(
    proxy_count=1,
    proxy_list=["10.0."]  # Your VPC CIDR
)
```

### Cloudflare

```python
ipware = FastAPIIpWare(
    precedence=("CF-Connecting-IP",)
)
```

### Multiple Proxies (CDN + Load Balancer)

```python
ipware = FastAPIIpWare(
    proxy_count=2,
    proxy_list=["10.1.", "10.2."]  # CDN and LB IPs
)
```

### NGINX Reverse Proxy

```python
ipware = FastAPIIpWare(
    precedence=("X-Real-IP", "X-Forwarded-For"),
    proxy_count=1
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

## Default Header Precedence

The default precedence order is optimized for modern cloud deployments:

1. `X-Forwarded-For` - Most common, used by AWS ELB, nginx, etc.
2. `X-Real-IP` - NGINX
3. `CF-Connecting-IP` - Cloudflare
4. `True-Client-IP` - Cloudflare Enterprise
5. `Fastly-Client-IP` - Fastly, Firebase
6. `X-Client-IP` - Microsoft Azure
7. `X-Cluster-Client-IP` - Rackspace Cloud Load Balancers
8. `Forwarded-For` - RFC 7239
9. `Forwarded` - RFC 7239
10. `Client-IP` - Akamai, Cloudflare

## Why fastapi-ipware?

### The Problem

`python-ipware` expects WSGI-style headers (e.g., `HTTP_X_FORWARDED_FOR`), but FastAPI/Starlette uses natural header names (e.g., `X-Forwarded-For`). This requires a manual conversion "hack":

```python
# The old way - manual conversion needed
meta_dict = {}
for name, value in request.headers.items():
    meta_key = f"HTTP_{name.upper().replace('-', '_')}"
    meta_dict[meta_key] = value

ip, trusted = ipw.get_client_ip(meta=meta_dict)
```

### The Solution

`fastapi-ipware` handles this conversion internally and efficiently:

```python
# The new way - clean and simple
ipware = FastAPIIpWare()
ip, trusted = ipware.get_client_ip_from_request(request)
```

Performance benefits:
- Header format conversion happens **once at initialization**, not on every request
- Request headers converted **once per request** (unavoidable)
- Zero overhead during header lookup (O(1) dict operations)

## API Reference

### `FastAPIIpWare`

```python
FastAPIIpWare(
    precedence: Optional[Tuple[str, ...]] = None,
    leftmost: bool = True,
    proxy_count: Optional[int] = None,
    proxy_list: Optional[List[str]] = None,
)
```

**Parameters:**
- `precedence`: Tuple of header names to check (uses natural names with dashes)
- `leftmost`: If True, use leftmost IP in comma-separated list (standard behavior)
- `proxy_count`: Expected number of proxies (for validation)
- `proxy_list`: List of trusted proxy IP prefixes

### `get_client_ip_from_request`

```python
get_client_ip_from_request(
    request: Request,
    strict: bool = False
) -> Tuple[Optional[IPAddress], bool]
```

**Parameters:**
- `request`: FastAPI/Starlette Request object
- `strict`: If True, enforce exact proxy count/list match

**Returns:**
- Tuple of `(ip_address, trusted_route)` where:
  - `ip_address`: IPv4Address or IPv6Address object (or None)
  - `trusted_route`: True if request came through validated proxies

## Contributing

Contributions welcome! This is a thin wrapper around python-ipware, so most IP detection logic lives there.

## License

MIT

## Credits

Built on top of [python-ipware](https://github.com/un33k/python-ipware) by un33k.
