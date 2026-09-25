from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastapi_ipware import FastAPIIpWare


def create_app(precedence: tuple[str, ...] | None = None) -> FastAPI:
    ipware = FastAPIIpWare(precedence=precedence)
    app = FastAPI()

    @app.get("/")
    def index(request: Request) -> dict[str, str | bool | None]:
        ip, trusted = ipware.get_client_ip_from_request(request)

        return {
            "ip": str(ip) if ip else None,
            "trusted": trusted,
        }

    return app


def test_fastapi_request_x_forwarded_for() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/", headers={"X-Forwarded-For": "203.0.113.5"})

    assert response.json()["ip"] == "203.0.113.5"


def test_fastapi_request_cf_connecting_ip() -> None:
    app = create_app(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
    client = TestClient(app)

    response = client.get("/", headers={"CF-Connecting-IP": "198.51.100.42"})

    assert response.json()["ip"] == "198.51.100.42"


def test_fastapi_request_custom_client_ip() -> None:
    app = create_app()
    client = TestClient(app, client=("198.51.100.23", 5150))

    response = client.get("/")

    assert response.json()["ip"] == "198.51.100.23"


def test_fastapi_depends_injection() -> None:
    from typing import Annotated

    from fastapi import Depends

    from fastapi_ipware import ClientIpResult, IpAddressType

    ipware = FastAPIIpWare()
    strict_dep = ipware.dependency(strict=True)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    @app.get("/ip-only")
    def get_only_ip(
        ip: Annotated[IpAddressType | None, Depends(ipware.get_ip)],
    ) -> dict[str, str | None]:
        return {"ip": str(ip) if ip else None}

    @app.get("/ip-str")
    def get_only_ip_str(
        ip_str: Annotated[str | None, Depends(ipware.get_ip_str)],
    ) -> dict[str, str | None]:
        return {"ip": ip_str}

    @app.get("/strict-dep")
    def get_strict(
        client: Annotated[ClientIpResult, Depends(strict_dep)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    client = TestClient(app)

    res1 = client.get("/client", headers={"X-Forwarded-For": "203.0.113.10"})
    assert res1.json() == {"ip": "203.0.113.10", "trusted": False}

    res2 = client.get("/ip-only", headers={"X-Forwarded-For": "203.0.113.10"})
    assert res2.json() == {"ip": "203.0.113.10"}

    res3 = client.get("/ip-str", headers={"X-Forwarded-For": "203.0.113.10"})
    assert res3.json() == {"ip": "203.0.113.10"}

    res4 = client.get("/strict-dep", headers={"X-Forwarded-For": "203.0.113.10"})
    assert res4.json() == {"ip": "203.0.113.10", "trusted": False}


def test_ipware_middleware_http() -> None:
    from fastapi_ipware import IpWareMiddleware

    app = FastAPI()
    app.add_middleware(IpWareMiddleware)

    @app.get("/state")
    def state_endpoint(request: Request) -> dict[str, str | bool | None]:
        return {
            "ip": str(request.state.client_ip) if request.state.client_ip else None,
            "trusted": request.state.ip_trusted,
            "ip_str": request.state.client_ip_str,
        }

    client = TestClient(app)
    res = client.get("/state", headers={"X-Forwarded-For": "203.0.113.25"})
    assert res.json() == {
        "ip": "203.0.113.25",
        "trusted": False,
        "ip_str": "203.0.113.25",
    }


def test_ipware_middleware_websocket() -> None:
    from fastapi import WebSocket

    from fastapi_ipware import IpWareMiddleware

    app = FastAPI()
    app.add_middleware(IpWareMiddleware)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json(
            {
                "ip": str(websocket.state.client_ip)
                if websocket.state.client_ip
                else None,
                "trusted": websocket.state.ip_trusted,
                "ip_str": websocket.state.client_ip_str,
            }
        )
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect(
        "/ws", headers={"X-Forwarded-For": "203.0.113.50"}
    ) as ws:
        data = ws.receive_json()
        assert data == {
            "ip": "203.0.113.50",
            "trusted": False,
            "ip_str": "203.0.113.50",
        }


# Two proxies on the right of the client. proxy_count=1 is a strict mismatch.
MISMATCHED_FORWARDED_FOR = {"X-Forwarded-For": "203.0.113.10, 10.0.0.1, 10.0.0.2"}


def test_depends_honors_default_strict() -> None:
    from typing import Annotated

    from fastapi import Depends

    from fastapi_ipware import ClientIpResult

    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    @app.get("/factory")
    def get_factory(
        client: Annotated[ClientIpResult, Depends(ipware.dependency())],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    @app.get("/loose")
    def get_loose(
        client: Annotated[ClientIpResult, Depends(loose)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    client = TestClient(app)

    assert client.get("/client", headers=MISMATCHED_FORWARDED_FOR).json() == {
        "ip": None,
        "trusted": False,
    }
    assert client.get("/factory", headers=MISMATCHED_FORWARDED_FOR).json() == {
        "ip": None,
        "trusted": False,
    }
    assert client.get("/loose", headers=MISMATCHED_FORWARDED_FOR).json() == {
        "ip": "10.0.0.1",
        "trusted": True,
    }


def test_depends_proxy_list_honors_default_strict() -> None:
    from typing import Annotated

    from fastapi import Depends

    from fastapi_ipware import ClientIpResult

    ipware = FastAPIIpWare(proxy_list=["10.0.0."], default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    @app.get("/loose")
    def get_loose(
        client: Annotated[ClientIpResult, Depends(loose)],
    ) -> dict[str, str | bool | None]:
        ip, trusted = client
        return {"ip": str(ip) if ip else None, "trusted": trusted}

    client = TestClient(app)

    assert client.get("/client", headers=MISMATCHED_FORWARDED_FOR).json() == {
        "ip": None,
        "trusted": False,
    }
    assert client.get("/loose", headers=MISMATCHED_FORWARDED_FOR).json() == {
        "ip": "10.0.0.1",
        "trusted": True,
    }


def test_middleware_honors_default_strict() -> None:
    from fastapi_ipware import IpWareMiddleware

    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    app = FastAPI()
    app.add_middleware(IpWareMiddleware, ipware=ipware)

    @app.get("/state")
    def state_endpoint(request: Request) -> dict[str, str | bool | None]:
        return {
            "ip": str(request.state.client_ip) if request.state.client_ip else None,
            "trusted": request.state.ip_trusted,
            "ip_str": request.state.client_ip_str,
        }

    res = TestClient(app).get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {"ip": None, "trusted": False, "ip_str": None}


def test_middleware_strict_override() -> None:
    from fastapi_ipware import IpWareMiddleware

    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    app = FastAPI()
    app.add_middleware(IpWareMiddleware, ipware=ipware, strict=False)

    @app.get("/state")
    def state_endpoint(request: Request) -> dict[str, str | bool | None]:
        return {
            "ip": str(request.state.client_ip) if request.state.client_ip else None,
            "trusted": request.state.ip_trusted,
            "ip_str": request.state.client_ip_str,
        }

    res = TestClient(app).get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {
        "ip": "10.0.0.1",
        "trusted": True,
        "ip_str": "10.0.0.1",
    }


def test_middleware_proxy_list_honors_default_strict() -> None:
    from fastapi_ipware import IpWareMiddleware

    ipware = FastAPIIpWare(proxy_list=["10.0.0."], default_strict=True)
    app = FastAPI()
    app.add_middleware(IpWareMiddleware, ipware=ipware)

    @app.get("/state")
    def state_endpoint(request: Request) -> dict[str, str | bool | None]:
        return {
            "ip": str(request.state.client_ip) if request.state.client_ip else None,
            "trusted": request.state.ip_trusted,
            "ip_str": request.state.client_ip_str,
        }

    res = TestClient(app).get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {"ip": None, "trusted": False, "ip_str": None}


def test_depends_websocket() -> None:
    from typing import Annotated

    from fastapi import Depends, WebSocket

    from fastapi_ipware import ClientIpResult

    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> None:
        await websocket.accept()
        ip, trusted = client
        await websocket.send_json({"ip": str(ip) if ip else None, "trusted": trusted})
        await websocket.close()

    @app.websocket("/ws-loose")
    async def websocket_loose(
        websocket: WebSocket,
        client: Annotated[ClientIpResult, Depends(loose)],
    ) -> None:
        await websocket.accept()
        ip, trusted = client
        await websocket.send_json({"ip": str(ip) if ip else None, "trusted": trusted})
        await websocket.close()

    client = TestClient(app)

    with client.websocket_connect("/ws", headers=MISMATCHED_FORWARDED_FOR) as ws:
        assert ws.receive_json() == {"ip": None, "trusted": False}

    with client.websocket_connect("/ws-loose", headers=MISMATCHED_FORWARDED_FOR) as ws:
        assert ws.receive_json() == {"ip": "10.0.0.1", "trusted": True}
