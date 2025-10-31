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

The default precedence order is optimized for modern cloud deployments. See the [default precedence configuration](https://github.com/iloveitaly/fastapi-ipware/blob/main/fastapi_ipware/__init__.py#L48-L58) in the source code.

## Why fastapi-ipware?

`python-ipware` expects WSGI-style headers (`HTTP_X_FORWARDED_FOR`), but FastAPI uses natural header names (`X-Forwarded-For`). This wrapper handles the conversion automatically so you don't have to.

## Contributing

Contributions welcome! This is a thin wrapper around python-ipware, so most IP detection logic lives there.

## License

[MIT License](LICENSE.md)

## Credits

Built on top of [python-ipware](https://github.com/un33k/python-ipware) by un33k.
