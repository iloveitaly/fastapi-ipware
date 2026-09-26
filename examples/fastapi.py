"""
Example FastAPI application using fastapi-ipware to extract client IP addresses.

Run with: uvicorn examples.fastapi:app --reload
"""

from typing import Annotated

from fastapi import Depends, FastAPI, Request

from fastapi_ipware import ClientIpResult, FastAPIIpWare

app = FastAPI()

# initialize with default settings
ipware = FastAPIIpWare()

# or customize for your infrastructure:
# ipware = FastAPIIpWare(
#     # cloudflare
#     precedence=("CF-Connecting-IP", "X-Forwarded-For"),
#     # expect 1 proxy
#     proxy_count=1,
#     # trust proxies from 10.0.x.x
#     proxy_list=["10.0."],
# )


@app.get("/")
async def get_client_ip(request: Request):
    "Get the client's IP address from the request"
    ip, trusted = ipware.get_client_ip_from_request(request)

    if not ip:
        return {"error": "Could not determine IP address"}

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


@app.get("/dep")
async def get_client_ip_dep(client: Annotated[ClientIpResult, Depends(ipware)]):
    "Get the client's IP using FastAPI dependency injection"
    ip, trusted = client

    return {"ip": str(ip) if ip else None, "trusted": trusted}


@app.get("/ip")
async def get_client_ip_str_dep(
    ip_str: Annotated[str | None, Depends(ipware.get_ip_str)],
):
    "Get just the IP string using FastAPI dependency injection"
    return {"ip": ip_str}


@app.get("/health")
async def health():
    "Health check endpoint"
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8_000)
