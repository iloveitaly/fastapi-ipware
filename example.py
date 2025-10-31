"""
Example FastAPI application using fastapi-ipware to extract client IP addresses.

Run with: uvicorn example:app --reload
"""

from fastapi import FastAPI, Request
from fastapi_ipware import FastAPIIpWare

app = FastAPI()

# Initialize with default settings
ipware = FastAPIIpWare()

# Or customize for your infrastructure:
# ipware = FastAPIIpWare(
#     precedence=("CF-Connecting-IP", "X-Forwarded-For"),  # Cloudflare
#     proxy_count=1,  # Expect 1 proxy
#     proxy_list=["10.0."]  # Trust proxies from 10.0.x.x
# )


@app.get("/")
async def get_client_ip(request: Request):
    """Get the client's IP address from the request."""
    ip, trusted = ipware.get_client_ip_from_request(request)

    if ip:
        return {
            "ip": str(ip),
            "trusted_route": trusted,
            "ip_type": {
                "is_global": ip.is_global,
                "is_private": ip.is_private,
                "is_loopback": ip.is_loopback,
                "is_multicast": ip.is_multicast,
            },
        }

    return {"error": "Could not determine IP address"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
