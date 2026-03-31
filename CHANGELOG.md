# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (`YYYY.M.INCREMENT`).

> This fork is based on [h4de5/home-assistant-vimar](https://github.com/h4de5/home-assistant-vimar).
> All changes listed below are relative to the original upstream `master` branch.

---

## [2026.3.0] - 2026-03-17

### Added

- **SAI2 alarm control panel**: full integration with the VIMAR SAI2 domestic alarm system. Each named area (group) is exposed as an `alarm_control_panel` entity with Disarm, Arm Away, Arm Home, and Arm Night actions. Automatic disarm-before-rearm when switching between armed modes. PIN protection via integration options. All entities grouped under a single "SAI Alarm" device.
- **SAI2 zone binary sensors**: each SAI2 zone (door contact, motion detector, tamper sensor, etc.) is exposed as a `binary_sensor` with automatic device class detection based on zone name keywords. Live state from parent object DPADD_OBJECT bitmask. Extra attributes: `raw_value`, `excluded`, `alarm`, `tampered`, `masked`, `memory`, `area`.
- **Re-authentication flow**: automatic reauth trigger when credentials expire or become invalid, with a user-friendly confirmation dialog in the HA UI.
- **`available` property**: entities now correctly report `unavailable` when the Vimar web server is unreachable, authentication fails, or a device is removed from the Vimar configuration.
- **Internationalization (i18n)**: config flow, options flow, and reauth flow fully translated into 7 languages — English, Italian, German, French, Spanish, Dutch, Portuguese.
- **Time-based cover position tracking**: covers report an estimated current position calculated from configurable travel times (`travel_time_up` / `travel_time_down`), with four operating modes: `legacy`, `native`, `time_based`, `auto`.
- **Relay delay compensation**: configurable offset to account for mechanical relay switching latency in cover position calculations.
- **Cover physical button detection**: movement triggered by physical wall switches is detected and distinguished from HA-initiated commands, keeping position tracking accurate.
- **Slim polling**: after the initial full discovery, subsequent update cycles query only the status IDs indexed at startup (`get_status_only()`), skipping all device/room JOINs. Reduces per-poll database workload by ~90% on embedded hardware.
- **Hash-based change detection**: each poll computes a lightweight hash of every device's status values. Only devices whose hash changed since the last cycle are propagated to Home Assistant.
- **Selective entity state writes**: `_handle_coordinator_update()` skips entities whose device has not changed (`_changed_device_ids` filter), reducing HA event-bus pressure on large installations.
- **Modular `vimarlink` architecture**: `vimarlink` refactored into a proper package with dedicated modules — `connection.py`, `device_queries.py`, `sql_parser.py`, `http_adapter.py`, `exceptions.py` — and a streamlined `vimarlink.py` facade.
- **`ConfigEntryAuthFailed` propagation**: the coordinator raises the correct HA exception type on authentication errors, enabling the automatic reauth flow.
- **Graceful transient error recovery**: SQL parsing errors return `None` instead of triggering re-authentication, preventing SSL handshake storms on overloaded web servers.
- **Compact poll logging**: two summary DEBUG lines per cycle (`Updated (N): name1, name2, ...` / `Skipped (N): name1, name2, ...`) replacing one line per entity per cycle.
- **GitHub project scaffolding**: issue templates (bug report, feature request), pull request template, CI/CD workflow, `CONTRIBUTING.md`, `CODEOWNERS`.

### Fixed

- **UI desync after consecutive actions on monostable devices**: `request_statemachine_update()` now invalidates the device's cached hash after every optimistic write.
- **`_changed_device_ids` overwritten by slim poll**: `_detect_state_changes()` now merges new IDs into the existing set (`.update()`) instead of replacing it.
- **`_changed_device_ids` carrying stale IDs across cycles**: the set is now cleared at the beginning of each `_async_update_data()` cycle.
- **Class-level mutable attributes shared across config entries**: `_device_state_hashes`, `_changed_device_ids`, `_known_status_ids` in `VimarDataUpdateCoordinator`, and `_attributes` in `VimarEntity`, moved to `__init__()`.
- **`_device_state_hashes` not reset on reload**: `init_vimarproject()` now clears the hash map so stale hashes do not mask real state changes after a config reload.
- **`RecursionError` on large installations**: `get_paged_results()` converted from recursive to iterative `while` loop.
- **`ToggleEntity` deprecation**: `switch.py` updated to inherit from `SwitchEntity`.
- **`is_default_state` wrong value for off state**: fixed to `not self.is_on`.
- **`assumed_state` inverted logic**: corrected to return `True` when state is assumed, `False` when known.
- **`_LOGGER_isDebug` stale at import time**: replaced with `_LOGGER.isEnabledFor(logging.DEBUG)` evaluated at runtime.
- **`_device_overrides` and `vimarconfig` shared across customizer instances**: moved to `__init__()`.
- **SSL ignore warning logged on every request**: replaced with instance attribute `_ssl_ignore_logged`.
- **`AttributeError` on empty SQL payload**: added `None` guard in `parse_sql_payload()`.
- **`format_name()` silent truncation**: restored original sequential `replace()` chain.
- **`extra_state_attributes` accumulating stale keys**: fixed by returning a fresh `dict` on every call.
- **`get_remote_devices_query` duplicate columns**: removed duplicate `object_name` and `object_type` from `SELECT` clause.
- **`async_remove_old_devices()` never removing stale devices**: fixed identifier comparison to use `frozenset`.
- **`entry.state.name` fragile string comparison**: replaced with `async_config_entry_first_refresh()`.
- **`CONF_OVERRIDE` propagated as `None`**: fixed with `or []` guard.
- **Cover `TypeError` on first `set_cover_position` call**: added `None` guard for `_tb_position`.
- **Cover physical button false-positives**: added `_tb_ha_command_active` flag.
- **Duplicate device names in poll log**: deduplicated by `device_id` using a `seen_ids` set.
- **Cover UI update granularity**: `UI_UPDATE_THRESHOLD` reduced from 2% to 1%.
- **Optimized SQL queries**: removed duplicate columns, reordered `WHERE` clauses, added `DISTINCT` to `GROUP_CONCAT`.
- **O(n²) device-hash computation**: replaced with a single `"".join()` call.
- **`change_state()` code duplication**: extracted into `_apply_state_change()` helper.

---

## Version Numbering

This project uses [Calendar Versioning](https://calver.org/) with the `YYYY.M.INCREMENT` scheme:
- `YYYY` — year of release
- `M` — month of release (1–12, no leading zero)
- `INCREMENT` — incremental release within the same month (starting from 0)
