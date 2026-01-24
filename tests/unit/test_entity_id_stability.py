"""Test entity ID stability - CRITICAL for backward compatibility.

NO Home Assistant dependencies required.
"""
import pytest
import sys
import os

# Add path to find vimarlink
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'custom_components', 'vimar'))

from vimarlink.vimarlink import VimarProject, VimarLink

pytestmark = pytest.mark.no_ha  # No HA required


@pytest.fixture
def sample_light_device():
    """Sample light device dict."""
    return {
        'object_id': '768',
        'room_ids': ['439'],
        'room_names': ['Living Room'],
        'room_name': 'Living Room',
        'object_name': 'DIMMER 11 WOHNZIMMER',
        'object_type': 'CH_Dimmer_Automation',
        'status': {
            'on/off': {'status_id': '769', 'status_value': '1'},
            'livello': {'status_id': '770', 'status_value': '75'}
        },
    }


def test_object_id_never_modified(sample_light_device):
    """CRITICAL: Ensure object_id is never modified during parse_device_type.

    This test protects existing users' entity IDs from changing.
    Entity unique IDs in Home Assistant are based on object_id.
    """
    original_id = sample_light_device['object_id']

    link = VimarLink('https', '192.168.1.1', 443, 'user', 'pass')
    project = VimarProject(link)

    # Parse device type
    project.parse_device_type(sample_light_device)

    # CRITICAL: object_id must not change
    assert sample_light_device['object_id'] == original_id, \
        "object_id was modified! This breaks existing user setups!"
    assert sample_light_device['device_type'] == 'light'


@pytest.mark.parametrize("object_type,expected_platform,status", [
    # Devices that need specific status keys to be recognized
    ("CH_Dimmer_Automation", "light", {'on/off': {'status_value': '1'}, 'livello': {'status_value': '50'}}),
    ("CH_Shutter_Automation", "cover", {'up/down': {'status_value': '0'}}),
    ("CH_HVAC", "climate", {'setpoint': {'status_value': '20'}}),
    # These are recognized by object_type prefix matching
    ("CH_Dimmer_RGB", "light", {'on/off': {'status_value': '1'}}),
    ("CH_ShutterWithoutPosition_Automation", "cover", {'up/down': {'status_value': '0'}}),
])
def test_device_type_mapping(object_type, expected_platform, status):
    """Test device type mappings preserve object_id."""
    device = {
        'object_id': '123',
        'object_type': object_type,
        'object_name': 'TEST DEVICE',
        'status': status
    }

    original_id = device['object_id']

    link = VimarLink('https', '192.168.1.1', 443, 'user', 'pass')
    project = VimarProject(link)
    project.parse_device_type(device)

    assert device['object_id'] == original_id, "object_id changed!"
    assert device['device_type'] == expected_platform


def test_object_id_preserved_for_unknown_type():
    """Test that object_id is preserved even for unknown device types."""
    device = {
        'object_id': '999',
        'object_type': 'CH_Unknown_Device_Type',
        'object_name': 'UNKNOWN DEVICE',
        'status': {}
    }

    original_id = device['object_id']

    link = VimarLink('https', '192.168.1.1', 443, 'user', 'pass')
    project = VimarProject(link)
    project.parse_device_type(device)

    # object_id must NEVER change, even for unknown types
    assert device['object_id'] == original_id, "object_id changed for unknown type!"
    # Unknown types go to 'other' bucket
    assert device['device_type'] == 'other'
