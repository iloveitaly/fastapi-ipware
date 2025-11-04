# Get Real Client IPs in FastAPI Without WSGI Headaches

I built this after getting tired of manually converting headers to WSGI format just to use [python-ipware](https://github.com/un33k/python-ipware) with FastAPI. If you're running behind Cloudflare, AWS load balancers, or any proxy setup, you know the pain: python-ipware wants `HTTP_X_FORWARDED_FOR`, but FastAPI gives you `X-Forwarded-For`. This wrapper handles that conversion so you don't have to think about it.

The library does the header conversion once at initialization and once per request, then leverages all the battle-tested IP detection logic from python-ipware. Works with any proxy configuration—single load balancer, CDN + load balancer, Cloudflare, you name it.

## Installation

```bash
pip install fastapi-ipware
```

Or with uv:

```bash
uv add fastapi-ipware
```

## Usage

### Basic Example

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

### Custom Header Precedence

Tell the library which headers to check and in what order:

```python
# Cloudflare setup
ipware = FastAPIIpWare(
    precedence=("CF-Connecting-IP", "X-Forwarded-For")
)

# NGINX configuration
ipware = FastAPIIpWare(
    precedence=("X-Real-IP", "X-Forwarded-For")
)
```

### Proxy Count Validation

If you know exactly how many proxies sit between your users and your app, you can validate that:

```python
# Expect exactly 1 proxy (e.g., AWS ALB)
ipware = FastAPIIpWare(proxy_count=1)

# Strict mode: must be exactly 1 proxy
ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

# Non-strict mode: allow 1 or more proxies
ip, trusted = ipware.get_client_ip_from_request(request, strict=False)
```

### Trusted Proxy Lists

Validate that requests pass through specific trusted proxies:

```python
# Trust specific proxy IP prefixes
ipware = FastAPIIpWare(
    proxy_list=["10.0.", "10.1."]  # Your VPC CIDR ranges
)

ip, trusted = ipware.get_client_ip_from_request(request)
# trusted=True only if request came through specified proxies
```

### Real-World Deployment Examples

**AWS Application Load Balancer:**
```python
ipware = FastAPIIpWare(
    proxy_count=1,
    proxy_list=["10.0."]  # Your VPC CIDR
)
```

**Cloudflare:**
```python
ipware = FastAPIIpWare(
    precedence=("CF-Connecting-IP",)
)
```

**Multiple Proxies (CDN + Load Balancer):**
```python
ipware = FastAPIIpWare(
    proxy_count=2,
    proxy_list=["10.1.", "10.2."]  # CDN and LB IPs
)
```

**NGINX Reverse Proxy:**
```python
ipware = FastAPIIpWare(
    precedence=("X-Real-IP", "X-Forwarded-For"),
    proxy_count=1
)
```

## Features

- Works directly with FastAPI/Starlette `Request` objects—no manual header conversion
- Configure header precedence for your specific infrastructure (Cloudflare, AWS, NGINX, etc.)
- Validate proxy count to ensure requests pass through expected infrastructure
- Trusted proxy lists to verify requests come from known proxies
- Automatic preference for public IPs over private/loopback addresses
- Full IPv4 and IPv6 support
- Returns Python `ipaddress` objects with useful properties (`is_global`, `is_private`, etc.)

## How IP Detection Works

The returned IP object is a Python `ipaddress.IPv4Address` or `ipaddress.IPv6Address` with useful properties:

```python
ip, _ = ipware.get_client_ip_from_request(request)

if ip:
    print(f"Is public: {ip.is_global}")
    print(f"Is private: {ip.is_private}")
    print(f"Is loopback: {ip.is_loopback}")
    print(f"Is multicast: {ip.is_multicast}")
```

python-ipware automatically prefers public IPs over private IPs over loopback addresses when multiple IPs are available.

## Default Header Precedence

The library uses a sensible default that prioritizes provider-specific headers (CF-Connecting-IP, True-Client-IP, Fastly-Client-IP) over generic headers (X-Forwarded-For, X-Real-IP). Provider headers are more trustworthy since they're set by your CDN/proxy infrastructure and can't be spoofed by clients.

See the [full default precedence list](https://github.com/iloveitaly/fastapi-ipware/blob/main/fastapi_ipware/__init__.py#L48-L71) in the source code.

## Contributing

Contributions welcome! This is a thin wrapper around python-ipware, so most IP detection logic lives in that library.

## Credits

Built on [python-ipware](https://github.com/un33k/python-ipware) by un33k.

# [MIT License](LICENSE.md)
