"""Test that vimarlink can be imported without Home Assistant.

This is critical - vimarlink should work standalone.
"""
import pytest
import sys
import os

pytestmark = pytest.mark.no_ha  # No HA required


def test_vimarlink_imports_without_ha():
    """Test that vimarlink can be imported without Home Assistant installed."""
    # Add path
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "custom_components", "vimar"
        ),
    )

    # This should NOT raise ImportError
    from vimarlink.vimarlink import VimarLink, VimarProject

    # Verify classes are available
    assert VimarLink is not None
    assert VimarProject is not None


def test_vimarlink_can_be_instantiated():
    """Test that VimarLink can be created without HA."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "custom_components", "vimar"
        ),
    )

    from vimarlink.vimarlink import VimarLink

    # Should be able to create instance
    link = VimarLink("https", "192.168.1.1", 443, "user", "pass")

    assert link is not None
    assert link._schema == "https"
    assert link._host == "192.168.1.1"
    assert link._port == 443
