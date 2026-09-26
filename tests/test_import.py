"Test fastapi-ipware"

import fastapi_ipware


def test_import():
    "Test that the package can be imported"
    assert isinstance(fastapi_ipware.__name__, str)
    assert fastapi_ipware.__name__ == "fastapi_ipware"


def test_version():
    "Test that the version is available"
    assert isinstance(fastapi_ipware.__version__, str)
    assert len(fastapi_ipware.__version__) > 0


def test_public_exports():
    "Test all declared public exports"
    from fastapi_ipware import (
        DEFAULT_PRECEDENCE,
        Algorithm,
        ClientIpResult,
        FastAPIIpWare,
        IpAddressType,
        IpWareMiddleware,
        __all__,
        __version__,
    )

    expected_exports: set[str] = {
        "Algorithm",
        "ClientIpResult",
        "DEFAULT_PRECEDENCE",
        "FastAPIIpWare",
        "IpAddressType",
        "IpWareMiddleware",
        "__version__",
    }
    assert set(__all__) == expected_exports

    for export_name in __all__:
        assert hasattr(fastapi_ipware, export_name)

    assert FastAPIIpWare is not None
    assert IpWareMiddleware is not None
    assert Algorithm is not None
    assert ClientIpResult is not None
    assert IpAddressType is not None
    assert isinstance(DEFAULT_PRECEDENCE, tuple)
    assert len(DEFAULT_PRECEDENCE) > 0
    assert isinstance(__version__, str)
