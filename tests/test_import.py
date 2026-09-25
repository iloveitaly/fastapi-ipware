"""Test fastapi-ipware."""

import fastapi_ipware


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(fastapi_ipware.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(fastapi_ipware.__version__, str)


def test_public_exports() -> None:
    """Test all declared public exports."""
    from fastapi_ipware import (
        DEFAULT_PRECEDENCE,
        FastAPIIpWare,
        IpWareMiddleware,
        __all__,
    )

    assert FastAPIIpWare is not None
    assert IpWareMiddleware is not None
    assert isinstance(DEFAULT_PRECEDENCE, tuple)
    assert "FastAPIIpWare" in __all__
    assert "IpWareMiddleware" in __all__
