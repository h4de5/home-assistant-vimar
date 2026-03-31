# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for VIMAR By-Me/By-Web home automation systems. It enables Home Assistant to control and monitor VIMAR devices (lights, climates, covers, switches, sensors, media players, scenes) through the VIMAR web server (hardware models 01945/01946).

The integration uses local polling to communicate with the VIMAR web server via HTTP/HTTPS requests that mimic the By-me web interface.

## Architecture

### Core Components

**`vimarlink/vimarlink.py`** (1318 lines) - The communication layer

- `VimarLink` class: Handles authentication and HTTP communication with VIMAR web server
- `VimarProject` class: Manages device discovery, state tracking, and updates
- Custom `HTTPAdapter`: Supports old TLS versions (TLSv1) required by VIMAR hardware
- Parses XML responses from the web server to extract device states
- Maps VIMAR device types (`CH_*` channels) to Home Assistant platforms

**`vimar_coordinator.py`** (260 lines) - The data coordinator

- `VimarDataUpdateCoordinator`: Extends Home Assistant's `DataUpdateCoordinator`
- Manages polling intervals (default 8 seconds)
- Handles device registration and platform setup
- Coordinates state updates across all entities
- Manages connection state and re-authentication

**`vimar_entity.py`** (385 lines) - Base entity class

- `VimarEntity`: Abstract base class for all VIMAR entities
- Extends Home Assistant's `CoordinatorEntity`
- Provides common functionality for state updates and device info
- Handles the mapping between VIMAR device objects and Home Assistant entities

**Platform implementations** - Individual entity types

- `alarm_control_panel.py` - SAI2 alarm area control (arm/disarm, multi-area, PIN)
- `binary_sensor.py` - Connection status + SAI2 zone sensors (door, motion, tamper)
- `climate.py` - HVAC/thermostat control
- `cover.py` - Covers/shutters/blinds with time-based position tracking
- `light.py` - Light and RGB dimmer control
- `media_player.py` - Audio device control
- `scene.py` - Scene activation
- `sensor.py` - Sensors including energy monitors
- `switch.py` - Switches and outlets

**Configuration**

- `config_flow.py` (320 lines) - GUI configuration flow and options
- `const.py` (99 lines) - Constants and platform mappings
- `__init__.py` (223 lines) - Integration setup, services, and entry management

**Device customization**

- `vimar_device_customizer.py` (331 lines) - Allows overriding device types via regex patterns

### Data Flow

1. **Initialization**: `async_setup_entry()` creates a `VimarDataUpdateCoordinator` which initializes `VimarLink` and `VimarProject`
2. **Authentication**: `VimarLink` logs into the web server and maintains session
3. **Device Discovery**: `VimarProject.update()` polls the web server for device states via XML requests
4. **State Management**: Coordinator distributes updates to all platform entities
5. **State Changes**: Entity methods call `VimarLink` to send commands back to web server

### Key Patterns

- Uses executor jobs (`hass.async_add_executor_job`) for synchronous VIMAR communication
- Custom SSL context to support old VIMAR firmware (TLSv1, AES256-SHA cipher)
- Device objects are TypedDict structures with status dictionaries
- Unique IDs are prefixed with `entry.unique_id` for multi-instance support
- Config can be imported from YAML but GUI config flow is preferred

## Development Commands

### Setup Development Environment

**Python Version:** This project requires Python 3.13+ (see pyrightconfig.json).

The environment has:

- Python 3.13.2 available via `python3.13`
- Python 3.11.2 available via `python3`
- `python3.13-venv` package installed

**Setup:**

```bash
# Create virtual environment with Python 3.13
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.13.2

# Install dependencies
pip install -r requirements_dev.txt

# Verify tools installed
pytest --version
pyright --version
ruff --version
```

**IMPORTANT - Always use Python 3.13:**

- Always use `python3.13` when creating the virtual environment
- After activation, always verify with `python --version` (should show 3.13.x)
- When running commands outside the venv, use `.venv/bin/python` explicitly
- NEVER use `python3` as it may point to Python 3.11 on some systems
- This ensures compatibility with Home Assistant 2026.1+ requirements

**Installing Python 3.13 on Debian/Ubuntu:**
If Python 3.13 is not available on your system, you can install it from backports:

```bash
# For Debian 12 (Bookworm) or similar systems
# See: https://community.home-assistant.io/t/python-3-12-backport-for-debian-12-bookworm/709459s
# for python 3.13
# See: https://community.home-assistant.io/t/python-3-13-backport-for-debian-12-bookworm/842333

# Add Debian backports repository (if not already added)
echo "deb http://deb.debian.org/debian bookworm-backports main" | sudo tee /etc/apt/sources.list.d/backports.list

# Update package list
sudo apt update

# Install Python 3.13 and venv
sudo apt install -y python3.13 python3.13-venv python3.13-dev && sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 2 && sudo update-alternatives --set python3 /usr/bin/python3.13

# Verify installation
python3.13 --version
```

### Validation and Testing

```bash
# HACS validation - runs via GitHub Actions
# See .github/workflows/validate.yml

# hassfest validation - runs via GitHub Actions
# See .github/workflows/hassfest.yml

# Type checking with pyright
pyright custom_components/vimar
```

### Using the vimarlink Library Standalone

**IMPORTANT:** The vimarlink library and examples/example.py are designed to work WITHOUT Home Assistant dependencies. They only require the `requests` package.

```bash
# From the repository root directory
cd /workspaces/home-assistant-vimar

# Create venv if it doesn't exist (MUST use Python 3.13)
python3.13 -m venv .venv

# Activate the venv
source .venv/bin/activate

# Install minimal dependencies (NO Home Assistant required)
pip install requests

# Setup credentials
cd examples
cp credentials.cfg.dist credentials.cfg
# Edit credentials.cfg with your VIMAR server details:
#   host=<your-vimar-server-ip>
#   username=<your-username>
#   password=<your-password>
#   certificate=  (leave empty to skip SSL verification for expired certs)

# Set PYTHONPATH to find vimarlink module
export PYTHONPATH=../custom_components/vimar

# List all available platforms and device counts
python example.py

# List all devices for a specific platform
# Valid platforms: light, cover, switch, climate, media_player, scene, sensor
python example.py --platform light
python example.py --platform cover
python example.py --platform climate
python example.py --platform switch
python example.py --platform media_player
python example.py --platform scene
python example.py --platform sensor

# Show a specific device's status
python example.py --platform light --device <device_id>

# Control a device
python example.py --platform cover --device 721 "up/down=0"
python example.py --platform lights --device 123 --status on/off --value 1
```

**Credentials Configuration (examples/credentials.cfg):**

```ini
[webserver]
schema=https
host=192.168.0.13        ; Your VIMAR server IP
port=443
username=admin           ; Your username
password=yourpassword    ; Your password
certificate=             ; Leave empty to skip SSL verification (for expired certs)
timeout=5
```

**Dependency Separation:**

- `vimarlink/` - Standalone library with NO Home Assistant dependencies
- `examples/example.py` - Standalone debug tool with NO Home Assistant dependencies
- `custom_components/vimar/*.py` - Integration code that DOES depend on Home Assistant

### Home Assistant Integration

Install in Home Assistant:

- Copy `custom_components/vimar/` to your HA `config/custom_components/` directory
- Or install via HACS (recommended)
- Restart Home Assistant
- Add integration via UI (Configuration → Integrations → Add Integration → VIMAR By-Me Hub)

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.vimar: debug
```

### Integration Services

The integration provides custom services:

- `vimar.update_entities` - Force update all entities
- `vimar.exec_vimar_sql` - Execute raw SQL on VIMAR database (advanced)
- `vimar.reload` - Reload the integration

## Important Technical Details

### VIMAR Device Types

The VIMAR system uses channel types (e.g., `CH_Luce`, `CH_VariatoreLuce`, `CH_HVAC_*`) which are mapped to Home Assistant platforms in `vimarlink.py`. Unknown device types are logged as warnings with their full state dictionaries - this is how new device types are discovered.

### SSL/TLS Requirements

VIMAR web servers use old TLS versions. The `HTTPAdapter` class in `vimarlink.py` must:

- Support TLSv1 (minimum version)
- Use AES256-SHA cipher
- Disable hostname verification
- Handle self-signed certificates via the `certificate` config option

### State Management

Device states are stored in dictionaries with this structure:

```python
{
  'status_id': str,      # Unique status identifier
  'status_value': str,   # Current value
  'status_range': str    # Range/options (e.g., "min=0|max=100")
}
```

State changes use `SETVALUE` XML operations targeting specific `status_id` values.

### Multi-Instance Support

The integration supports multiple VIMAR web servers. Each config entry has a unique_id (slugified title) used to prefix entity IDs and avoid conflicts.

## Common Tasks

### Adding Support for New Device Types

1. Enable debug logging to see "Unknown object returned" warnings
2. Capture the device's `object_type` (CH\_\* name) and full status dictionary
3. Add mapping in `vimarlink.py` in `get_device_type_from_device_object()`
4. Create or extend platform file (e.g., `light.py`, `switch.py`)
5. Test state reading and writing via the web server's network inspector

See CONTRIBUTING.md for detailed instructions on capturing device data.

### Modifying State Update Logic

The polling logic is in `VimarDataUpdateCoordinator._async_update_data()`. The update interval is configurable via `CONF_SCAN_INTERVAL` (default 8 seconds).

### Handling Configuration Changes

Config flow is in `config_flow.py`. Options can be changed via `async_step_init()` in `OptionsFlowHandler`. After options change, the entry is reloaded via `async_reload_entry()`.

## Repository Structure

```
custom_components/vimar/
  vimarlink/
    vimarlink.py          # Core VIMAR communication library
  __init__.py             # Integration setup and services
  config_flow.py          # Configuration UI
  const.py                # Constants
  vimar_coordinator.py    # Update coordinator
  vimar_entity.py         # Base entity class
  vimar_device_customizer.py  # Device override logic
  [platform].py           # Individual platform implementations

examples/
  example.py              # Standalone vimarlink usage
  credentials.cfg.dist    # Template for credentials

.github/workflows/
  validate.yml            # HACS validation
  hassfest.yml            # Home Assistant validation
```

## Compatibility

- **Home Assistant**: Requires 2026.1.0+ (see manifest.json)
- **Python**: 3.13+ (see pyrightconfig.json)
- **VIMAR Firmware**: Tested with v2.5 to v2.11
- **Hardware**: VIMAR 01945 or 01946 web server required

## Migration Notes

If upgrading from versions before May 2021, the integration was renamed from `vimar_platform` to `vimar`. This requires updating `.storage/core.entity_registry` and `configuration.yaml` - see README.md for migration steps.
