"""Test fastapi-ipware."""

import fastapi_ipware


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(fastapi_ipware.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(fastapi_ipware.__version__, str)
