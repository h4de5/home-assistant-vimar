[![HACS Validate](https://github.com/h4de5/home-assistant-vimar/actions/workflows/validate.yml/badge.svg)](https://github.com/h4de5/home-assistant-vimar/actions/workflows/validate.yml)
[![hassfest Validate](https://github.com/h4de5/home-assistant-vimar/actions/workflows/hassfest.yml/badge.svg)](https://github.com/h4de5/home-assistant-vimar/actions/workflows/hassfest.yml)
[![Github Release](https://img.shields.io/github/release/h4de5/home-assistant-vimar.svg)](https://github.com/h4de5/home-assistant-vimar/releases)
[![Github Commit since](https://img.shields.io/github/commits-since/h4de5/home-assistant-vimar/latest)](https://github.com/h4de5/home-assistant-vimar/releases)
[![Github Open Issues](https://img.shields.io/github/issues/h4de5/home-assistant-vimar.svg)](https://github.com/h4de5/home-assistant-vimar/issues)
[![Github Open Pull Requests](https://img.shields.io/github/issues-pr/h4de5/home-assistant-vimar.svg)](https://github.com/h4de5/home-assistant-vimar/pulls)

# VIMAR By-Me / By-Web Integration for Home Assistant

> **Current Version:** 2026.3.0 · **Requires:** Home Assistant 2026.1.0+ · **Python:** 3.13+

A comprehensive Home Assistant custom integration for the VIMAR By-me / By-web bus system. Controls lights, covers, climate, switches, sensors, media players, scenes, and the **SAI2 alarm system** through the VIMAR web server.

<img title="Lights, climates, covers" src="https://user-images.githubusercontent.com/6115324/84840393-b091e100-b03f-11ea-84b1-c77cbeb83fb8.png" width="900">
<img title="Energy guards" src="https://user-images.githubusercontent.com/51525150/89122026-3a005400-d4c4-11ea-98cd-c4b340cfb4c2.jpg" width="600">
<img title="Audio player" src="https://user-images.githubusercontent.com/51525150/89122129-36b99800-d4c5-11ea-8089-18c2dcab0938.jpg" width="300">

## 💻 Hardware Requirements

- **[Vimar 01945 - Web server By-me](https://www.vimar.com/de/int/catalog/obsolete/index/code/R01945)** or
- **[Vimar 01946 - Web server Light By-me](https://www.vimar.com/en/int/catalog/product/index/code/R01946)**

> **Note:** Tested with firmware versions v2.5 to v2.11. Always backup your Vimar database before firmware upgrades.

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **Custom Repositories**
3. Add: `https://github.com/h4de5/home-assistant-vimar`
4. Category: **Integration**
5. Install and restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/h4de5/home-assistant-vimar/releases)
2. Extract and copy `custom_components/vimar` to your HA `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

Configuration is fully managed via the Home Assistant UI.

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **VIMAR By-Me Hub**
4. Enter your web server credentials:
   - **Host:** IP address or hostname
   - **Port:** Usually `443` (HTTPS) or `80` (HTTP)
   - **Username:** Web server admin username
   - **Password:** Web server password
   - **SSL Certificate:** (Optional) Path to custom CA certificate

### Options Flow

After initial setup, click **Configure** on the integration to adjust:

- **Cover Position Mode:** `auto` (default), `native`, `time_based`, or `legacy`
- **SAI PIN:** 4-digit PIN for the SAI2 alarm system (required for alarm control)
- **Ignored Platforms:** Exclude specific platforms from discovery

## 🎯 Supported Devices

| Platform | Device Types | Status |
|----------|-------------|--------|
| **Light** | On/Off lights, Dimmers, RGB, White, Hue | ✅ Full Support |
| **Cover** | Shutters, Blinds — with native or time-based position tracking | ✅ Full Support |
| **Switch** | Generic switches, Outlets, Fans | ✅ Full Support |
| **Climate** | HVAC, Fancoils, Thermostats | ✅ Full Support |
| **Sensor** | Power meters, Energy guards, Temperature | ✅ Full Support |
| **Media Player** | Audio zones | ✅ Full Support |
| **Scene** | Vimar scenes | ✅ Full Support |
| **Alarm Control Panel** | SAI2 alarm areas — arm/disarm, multi-area, PIN protected | ✅ Full Support |
| **Binary Sensor** | SAI2 alarm zone sensors (door contacts, motion, tamper) + connection status | ✅ Full Support |

## 🚨 SAI2 Alarm System

Full integration with the VIMAR SAI2 domestic alarm system.

### Alarm Control Panel

Each SAI2 area is exposed as an `alarm_control_panel` entity supporting:

| Action | Description |
|--------|-------------|
| **Disarm** | Disarm the area |
| **Arm Away** | Full arming (all sensors active) |
| **Arm Home** | Internal arming (perimeter sensors only) |
| **Arm Night** | Partial arming |

**Features:**
- Multi-area support — each SAI2 group is a separate entity
- PIN protection via integration configuration
- Automatic disarm-before-rearm when switching between armed modes
- Live state from DPADD_OBJECT bitmask polling
- All entities grouped under a single **SAI Alarm** device

### Zone Binary Sensors

Each SAI2 zone is exposed as a `binary_sensor` with automatic device class detection:

| Zone Name Keywords | Device Class |
|-----------|--------------|
| porta, ingresso, basculante | `door` |
| finestra | `window` |
| volumetrico, PIR, motion | `motion` |
| sirena, manomissione, tamper | `tamper` |

**Extra attributes:** `raw_value`, `excluded`, `alarm`, `tampered`, `masked`, `memory`, `area`

### Setup

1. Configure the **SAI PIN** in integration options (the numeric code used on the Vimar web interface)
2. Alarm entities appear automatically after integration reload
3. Zone sensors update via slim poll (real-time parent bitmask)

## 🏠 Cover Position Tracking

Advanced position tracking for covers lacking native positional feedback.

### Operating Modes

| Mode | Description |
|------|-------------|
| **`auto`** (default) | Uses hardware sensor when available, falls back to time-based tracking |
| **`native`** | Hardware position sensors only |
| **`time_based`** | Always uses time-based calculation |
| **`legacy`** | Original master branch behavior (no tracking) |

### Travel Time Calibration

For accurate position tracking without hardware sensors:

1. Go to **Developer Tools** → **Services**
2. Select `vimar.set_travel_times`
3. Choose your cover entity
4. Enter measured times:
   - `travel_time_up`: Seconds from fully closed to fully open
   - `travel_time_down`: Seconds from fully open to fully closed

**Features:**
- 200ms internal calculation interval, UI state updated every 1% position change
- Position persistence across HA restarts
- Physical button detection (wall switches auto-sync to 0%/100%)
- Relay delay compensation for Vimar web server latency
- Per-entity travel time configuration via entity options

## 🛠️ Architecture

### Modular Structure

```
custom_components/vimar/
├── vimarlink/                    # Core library (HA-independent)
│   ├── connection.py            # HTTP & authentication
│   ├── device_queries.py        # SQL query builders
│   ├── exceptions.py            # Error classes
│   ├── http_adapter.py          # SSL/TLS legacy support
│   ├── sql_parser.py            # Response parser
│   ├── vimarlink.py             # Main API facade
│   ├── vimarlink_auth.py        # Auth with legacy TLS
│   └── vimarlink_protocol_async.py  # Async protocol
├── alarm_control_panel.py       # SAI2 alarm platform
├── binary_sensor.py             # Binary sensors + SAI2 zones
├── climate.py                   # HVAC / thermostats
├── config_flow.py               # UI configuration
├── const.py                     # Constants
├── cover.py                     # Covers with time-based tracking
├── light.py                     # Lights / dimmers / RGB
├── media_player.py              # Audio zones
├── scene.py                     # Scenes
├── sensor.py                    # Power / energy / temperature
├── switch.py                    # Switches / outlets
├── vimar_coordinator.py         # DataUpdateCoordinator
├── vimar_device_customizer.py   # Device type overrides
└── vimar_entity.py              # Base entity class
```

### Key Design Decisions

- **Slim polling:** After initial discovery, updates query only status IDs — ~90% less DB workload
- **Hash-based change detection:** Only devices with changed status hashes trigger HA state writes
- **Modular `vimarlink`:** Core library has zero HA dependencies, usable standalone
- **Re-authentication flow:** `ConfigEntryAuthFailed` triggers automatic reauth dialog
- **Entity availability:** Reports `unavailable` when web server is offline, auth fails, or device is removed

## 🐛 Troubleshooting

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.vimar: debug
    custom_components.vimar.vimarlink: debug
```

### Common Issues

#### SSL/Certificate Errors

**Problem:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions:**
1. Configure certificate path in integration settings
2. Integration auto-downloads certificates on first connection
3. Use HTTP instead of HTTPS (not recommended)

#### Connection Timeout

**Problem:** Web server doesn't respond

**Solutions:**
1. Check network connectivity and firewall rules
2. Increase timeout in integration options
3. Check web server load — create a dedicated HA user

#### Session Conflicts

**Problem:** Web GUI becomes unresponsive when HA is connected

**Solution:** Create a **dedicated user** on the Vimar web server for Home Assistant.

#### Cover Position Drift

**Problem:** Cover position becomes inaccurate over time

**Solutions:**
1. Recalibrate travel times with precise measurements
2. Perform full open/close cycle to auto-calibrate end-stops
3. Switch to `native` mode if hardware sensors are available

#### SAI2 Alarm Not Responding

**Problem:** Alarm entities appear but commands fail

**Solutions:**
1. Verify the **SAI PIN** is correct in integration options
2. Check that the Vimar web server user has SAI access permissions
3. Enable debug logging for `custom_components.vimar.alarm_control_panel`

## 🌍 Internationalization

Config flow, options flow, and reauth flow are fully translated in **7 languages**:

🇬🇧 English · 🇮🇹 Italian · 🇩🇪 German · 🇫🇷 French · 🇪🇸 Spanish · 🇳🇱 Dutch · 🇵🇹 Portuguese

## ⚠️ Disclaimer

**THIS IS A COMMUNITY-DRIVEN PROJECT.**

Use at your own risk. This integration mimics HTTP calls made through the official Vimar By-me web interface. While extensively tested, it is not officially supported by Vimar.

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 Report bugs via [Issues](https://github.com/h4de5/home-assistant-vimar/issues)
- ✨ Request features
- 🔧 Submit pull requests

## 📜 License

MIT License — see [LICENSE](LICENSE) file

## 🙏 Credits

**Maintainers:**
- [@h4de5](https://github.com/h4de5)
- [@robigan](https://github.com/robigan)
- [@davideciarmiello](https://github.com/davideciarmiello)

**Contributors:**
- [@WhiteWolf84](https://github.com/WhiteWolf84) — Architecture refactoring, performance optimizations, SAI2 alarm integration (powered by [Claude Opus](https://claude.ai))
- And all community members who reported issues and tested features!

---

**Star this repo if you find it useful! ⭐**
