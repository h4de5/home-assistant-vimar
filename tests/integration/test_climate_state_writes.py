"""Regression tests for climate state writes (Home Assistant required).

These cover the fix for the thermostat setpoint bug:
- change_state() must batch all values into a SINGLE executor job and send
  the SETVALUE requests sequentially, preserving the caller's order. Before
  the fix each value was dispatched as a separate fire-and-forget executor
  job, so concurrent requests reached the webserver out of order and the
  firmware reloaded its stored manual setpoint, discarding our write.
- async_set_temperature() must write ONLY the setpoint when the thermostat is
  already in manual mode (matching the native VIMAR web UI), and must apply
  funzionamento=MANUAL before the setpoint when activating from off/auto.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Import the integration as a package so relative imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from custom_components.vimar.climate import VimarClimate

pytestmark = pytest.mark.integration  # Home Assistant required

# Type II thermostat (heat_cool_fancoil) funzionamento values, see const.py.
FUNZ_MANUAL = "1"  # VIMAR_CLIMATE_MANUAL_II
FUNZ_OFF = "6"  # VIMAR_CLIMATE_OFF_II


def _make_climate(status):
    """Build a VimarClimate with mocked HA/bus dependencies.

    Bypasses CoordinatorEntity.__init__: the tested methods only read
    self._device and dispatch writes via self.hass.async_add_executor_job,
    which we capture without executing.
    """
    climate = VimarClimate.__new__(VimarClimate)
    climate._device = {"object_type": "CH_HVAC_FanCoil", "status": status}
    climate._device_id = "100"

    connection = MagicMock()
    connection.get_optionals_param.return_value = "NO-OPTIONALS"
    climate._vimarconnection = connection

    coordinator = MagicMock()
    coordinator._changed_device_ids = set()
    coordinator._device_state_hashes = {}
    climate._coordinator = coordinator

    climate.hass = MagicMock()
    climate._logger = MagicMock()
    # async_add_executor_job records the scheduled write without running it.
    climate.hass.async_add_executor_job = MagicMock()
    # Neutralize the HA state-machine write triggered after a change.
    climate.async_write_ha_state = MagicMock()
    return climate, connection


def _manual_fancoil_status():
    return {
        "funzionamento": {"status_id": "F", "status_value": FUNZ_MANUAL},
        "regolazione": {"status_id": "R", "status_value": "1"},  # -> heat_cool_fancoil
        "setpoint": {"status_id": "S", "status_value": "26.0"},
        "temperatura_misurata": {"status_id": "T", "status_value": "26.4"},
    }


def _scheduled_writes(climate):
    """Return the (status_id, value, optionals) list passed to the executor."""
    assert climate.hass.async_add_executor_job.call_count == 1
    func, writes = climate.hass.async_add_executor_job.call_args.args
    assert func == climate._write_states_sequentially
    return writes


def test_change_state_batches_into_single_ordered_job():
    """Multiple values -> one executor job, writes kept in the given order."""
    climate, _ = _make_climate(_manual_fancoil_status())

    climate.change_state(
        "funzionamento", FUNZ_MANUAL, "regolazione", "1", "setpoint", "21.5"
    )

    assert _scheduled_writes(climate) == [
        ("F", FUNZ_MANUAL, "NO-OPTIONALS"),
        ("R", "1", "NO-OPTIONALS"),
        ("S", "21.5", "NO-OPTIONALS"),
    ]


def test_change_state_updates_local_cache():
    """The optimistic local cache is updated for each written value."""
    climate, _ = _make_climate(_manual_fancoil_status())

    climate.change_state("setpoint", "21.5")

    assert climate._device["status"]["setpoint"]["status_value"] == "21.5"


def test_write_states_sequentially_preserves_order():
    """The executor body sends SETVALUE requests one-by-one, in order."""
    climate, connection = _make_climate({})
    writes = [("F", FUNZ_MANUAL, "O"), ("R", "1", "O"), ("S", "21.5", "O")]

    climate._write_states_sequentially(writes)

    sent = [tuple(call.args) for call in connection.set_device_status.call_args_list]
    assert sent == writes


async def test_set_temperature_in_manual_writes_only_setpoint():
    """Already in manual: a single setpoint SETVALUE, like the VIMAR web UI."""
    climate, _ = _make_climate(_manual_fancoil_status())

    await climate.async_set_temperature(temperature=21.5)

    assert _scheduled_writes(climate) == [("S", "21.5", "NO-OPTIONALS")]


async def test_set_temperature_when_off_activates_manual_then_setpoint():
    """From off: funzionamento=MANUAL is written first, setpoint last."""
    status = _manual_fancoil_status()
    status["funzionamento"]["status_value"] = FUNZ_OFF
    climate, _ = _make_climate(status)

    await climate.async_set_temperature(temperature=21.5)

    writes = _scheduled_writes(climate)
    # Only mode + setpoint are written; the heat/cool direction is untouched.
    assert [status_id for status_id, _, _ in writes] == ["F", "S"]
    assert writes[0] == ("F", FUNZ_MANUAL, "NO-OPTIONALS")
    assert writes[-1] == ("S", "21.5", "NO-OPTIONALS")
