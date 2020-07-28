"""Vimar Platform integration."""
from datetime import timedelta
import logging
import asyncio
import async_timeout
import os

from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.const import (
    CONF_PORT, CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_TIMEOUT)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
# from homeassistant.components.cover import (
#     DEVICE_CLASS_SHUTTER,
#     DEVICE_CLASS_WINDOW,
#     # DEVICE_CLASS_SHADE
# )
# from homeassistant.components.switch import (DEVICE_CLASS_OUTLET, DEVICE_CLASS_SWITCH)
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .vimarlink import (VimarLink, VimarProject, VimarApiError)
# from . import vimarlink

from .const import (
    DOMAIN,
    CONF_SCHEMA,
    CONF_CERTIFICATE,
    DEFAULT_USERNAME,
    DEFAULT_SCHEMA,
    DEFAULT_PORT,
    DEFAULT_CERTIFICATE,
    DEFAULT_TIMEOUT,
    DEVICE_TYPE_LIGHTS,
    DEVICE_TYPE_COVERS,
    DEVICE_TYPE_SWITCHES,
    DEVICE_TYPE_CLIMATES,
    # DEVICE_TYPE_SCENES,
    # DEVICE_TYPE_FANS,
    DEVICE_TYPE_SENSORS,
    # DEVICE_TYPE_OTHERS
)

# from . import vimarlink
# see some examples: https://github.com/pnbruckner/homeassistant-config/blob/master/custom_components/amcrest/__init__.py
# https://github.com/peterbuga/HASS-sonoff-ewelink/blob/master/sonoff/__init__.py

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SCHEMA, default=DEFAULT_SCHEMA): cv.string,
        vol.Optional(CONF_CERTIFICATE, default=DEFAULT_CERTIFICATE): vol.Any(cv.string, None),
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Range(min=2, max=60)
    })
}, extra=vol.ALLOW_EXTRA)

AVAILABLE_PLATFORMS = {
    DEVICE_TYPE_LIGHTS: 'light',
    DEVICE_TYPE_COVERS: 'cover',
    DEVICE_TYPE_SWITCHES: 'switch',
    DEVICE_TYPE_CLIMATES: 'climate',
    # DEVICE_TYPE_SCENES: '',
    # DEVICE_TYPE_FANS: 'fan',
    DEVICE_TYPE_SENSORS: 'sensor',
    # DEVICE_TYPE_OTHERS: ''
}


@asyncio.coroutine
async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Connect to the Vimar Webserver, verify login and read all devices."""
    devices = {}
    vimarconfig = config[DOMAIN]

    schema = vimarconfig.get(CONF_SCHEMA)
    host = vimarconfig.get(CONF_HOST)
    port = vimarconfig.get(CONF_PORT)
    username = vimarconfig.get(CONF_USERNAME)
    password = vimarconfig.get(CONF_PASSWORD)
    certificate = vimarconfig.get(CONF_CERTIFICATE)
    timeout = vimarconfig.get(CONF_TIMEOUT)

    # initialize a new VimarLink object
    vimarconnection = VimarLink(
        schema, host, port, username, password, certificate, timeout)

    # will hold all the devices and their states
    vimarproject = VimarProject(vimarconnection)

    # if certificate is set, but file is not there - download it from the
    # webserver
    if schema == "https" and certificate is not None and len(certificate) != 0:
        if os.path.isfile(certificate) is False:
            try:
                valid_certificate = await hass.async_add_executor_job(vimarconnection.install_certificate)

            except VimarApiError as err:
                _LOGGER.error("Certificate download error: %s", err)
                valid_certificate = False

            if not valid_certificate:
                raise PlatformNotReady

        else:

            _LOGGER.info(
                "Vimar CA Certificate is already in place: %s", certificate)

    # Verify that passed in configuration works
    # starting it outside MainThread

    try:
        valid_login = await hass.async_add_executor_job(vimarconnection.check_login)
    except VimarApiError as err:
        _LOGGER.error("Webserver %s: %s", host, err)
        valid_login = False
    except BaseException as err:
        _LOGGER.error("Login Exception: %s", err)
        valid_login = False

    if not valid_login:
        raise PlatformNotReady

    # save vimar connection into hass data to share it with other platforms
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["connection"] = vimarconnection
    hass.data[DOMAIN]["project"] = vimarproject

    # maingroups = await hass.async_add_executor_job(vimarconnection.get_main_groups)

    # if not maingroups or len(maingroups) == 0:
    #     _LOGGER.error(
    #         "Could not find any groups or rooms on Vimar Webserver %s", host)
    #     return False

    # # load devices
    # devices = await hass.async_add_executor_job(vimarconnection.get_room_devices, devices)
    # # add scenes to existing devices
    # devices = await hass.async_add_executor_job(vimarconnection.get_remote_devices, devices)

    async def async_api_update():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        see: https://developers.home-assistant.io/docs/integration_fetching_data/
        """
        try:
            _LOGGER.debug("Updating coordinator..")

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(6):
                # return await api.fetch_data()
                # return await hass.async_add_executor_job(vimarconnection.get_remote_devices)
                # return await hass.async_add_executor_job(_link.get_paged_results, _link.get_remote_devices)

                # self._devices = await self._link.get_paged_results(self._link.get_remote_devices)
                # return await vimarproject.update()
                # return await hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
                return await hass.async_add_executor_job(vimarproject.update)

                # return await vimarproject.update()

                # states = vimarconnection.get_scenes()
                # _LOGGER.debug("states in async_api_update %s", str(states))
                # return states
                # self._reset_status()
                # will yield logger debug message: Finished fetching vimar data in xx seconds

        except VimarApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    # see latest example https://github.com/home-assistant/core/blob/2088092f7cca4c82f940b3661b1ae47302670607/homeassistant/components/guardian/util.py
    # another example: https://github.com/home-assistant/core/blob/11b786a4fc39d3a31c8ab27045d88c9a437003b5/homeassistant/components/gogogate2/common.py
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="vimar",
        update_method=async_api_update,
        # update_method=vimarproject.async_api_update,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=8),
    )

    hass.data[DOMAIN]["coordinator"] = coordinator

    # initial refresh of all devices - replaces fetch of main groups and room devices
    # also fetches the initial states
    _LOGGER.debug("calling refresh..")
    await coordinator.async_refresh()
    _LOGGER.debug("done refresh")

    devices = coordinator.data

    # _LOGGER.info("Found devices %s", str(devices))

    if not devices or len(devices) == 0:
        _LOGGER.error("Could not find any devices on Vimar Webserver %s", host)
        return False

    # lights = {}
    # covers = {}
    # switches = {}
    # climates = {}
    # fans = {}
    # sensors = {}
    # others = {}

    # if len(devices) != 0:
    #     for device_id, device in devices.items():
    #         device_type, device_class, icon = parse_device_type(device)

    #         # _LOGGER.info("Found new device: " +
    #         # device_id + "/" + device["object_name"] + " " + device_type + " "
    #         # + (device_class if device_class else ""))

    #         device["device_type"] = device_type
    #         device["device_class"] = device_class
    #         device["icon"] = icon
    #         if device_type == DEVICE_TYPE_LIGHTS:
    #             lights[device_id] = device
    #         elif device_type == DEVICE_TYPE_COVERS:
    #             covers[device_id] = device
    #         elif device_type in [DEVICE_TYPE_SWITCHES, DEVICE_TYPE_SCENES]:
    #             switches[device_id] = device
    #         elif device_type == DEVICE_TYPE_CLIMATES:
    #             climates[device_id] = device
    #         elif device_type == DEVICE_TYPE_FANS:
    #             fans[device_id] = device
    #         elif device_type == DEVICE_TYPE_SENSORS:
    #             sensors[device_id] = device
    #         else:
    #             # _LOGGER.info("Found unknown device: " +
    #             #              device_type + "/" +
    #             #              (device_class if device_class else '-') + "/" +
    #             #              (icon if icon else '-'))
    #             others[device_id] = device

    # there should not be too many requests per second
    # limit scan_interval depending on items
    # scan_interval = max(3, int(len(devices) / 500 * 60)
    # hass.data[DOMAIN]["scan_interval"] = timedelta(seconds=scan_interval)

    # TODO: rework platform registration
    # according to: https://github.com/home-assistant/core/blob/83d4e5bbb734f77701073710beb74dd6b524195e/homeassistant/helpers/discovery.py#L131
    # https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/__init__.py#L143

    for device_type, platform in AVAILABLE_PLATFORMS.items():
        device_count = vimarproject.platform_exists(device_type)
        if device_count:
            _LOGGER.debug("load platform %s with %d %s", platform, device_count, device_type)
            hass.async_create_task(hass.helpers.discovery.async_load_platform(
                platform, DOMAIN, {"hass_data_key": device_type}, config))

    # save devices into hass data to share it with other platforms
    # if climates and len(climates) > 0:
    #     _LOGGER.debug("load platform climates..")
    #     hass.data[DOMAIN][DEVICE_TYPE_CLIMATES] = climates
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "climate", DOMAIN, {"hass_data_key": DEVICE_TYPE_CLIMATES}, config))
    # if lights and len(lights) > 0:
    #     _LOGGER.debug("load platform lights..")
    #     hass.data[DOMAIN][DEVICE_TYPE_LIGHTS] = lights
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "light", DOMAIN, {"hass_data_key": DEVICE_TYPE_LIGHTS}, config))
    # if covers and len(covers) > 0:
    #     _LOGGER.debug("load platform covers..")
    #     hass.data[DOMAIN][DEVICE_TYPE_COVERS] = covers
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "cover", DOMAIN, {"hass_data_key": DEVICE_TYPE_COVERS}, config))
    # if switches and len(switches) > 0:
    #     _LOGGER.debug("load platform switches..")
    #     hass.data[DOMAIN][DEVICE_TYPE_SWITCHES] = switches
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "switch", DOMAIN, {"hass_data_key": DEVICE_TYPE_SWITCHES}, config))
    # if sensors and len(sensors) > 0:
    #     _LOGGER.debug("load platform sensors..")
    #     hass.data[DOMAIN][DEVICE_TYPE_SENSORS] = sensors
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "sensor", DOMAIN, {"hass_data_key": DEVICE_TYPE_SENSORS}, config))
    # if fans and len(fans) > 0:
    #     hass.data[DOMAIN][DEVICE_TYPE_FANS] = fans
    #     hass.async_create_task(hass.helpers.discovery.async_load_platform(
    #         "fan", DOMAIN, {"hass_data_key": DEVICE_TYPE_FANS}, config))

    # States are in the format DOMAIN.OBJECT_ID.
    # hass.states.async_set("vimar_platform.Hello_World", "Works!")

    # Use `listen_platform` to register a callback for these events.
    # homeassistant.helpers.discovery.async_load_platform(hass, component, platform, discovered, hass_config)

    # Return boolean to indicate that initialization was successfully.
    return True


# async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry):
#     """Unload a UPnP/IGD device from a config entry."""
#     udn = config_entry.data["udn"]
#     device = hass.data[DOMAIN]["devices"][udn]

#     # remove port mapping
#     _LOGGER.debug("Deleting port mappings")
#     await device.async_delete_port_mappings()

#     # remove sensors
#     _LOGGER.debug("Deleting sensors")
#     dispatcher.async_dispatcher_send(hass, SIGNAL_REMOVE_SENSOR, device)

#     return True

    # def parse_device_type(self, device):
    #     """Split up devices into supported groups based on their names."""
    #     device_type = DEVICE_TYPE_OTHERS
    #     # see:
    #     # https://www.home-assistant.io/docs/configuration/customizing-devices/#device-class
    #     device_class = None
    #     # see: https://materialdesignicons.com/cdn/2.0.46/
    #     icon = None

    #     # mdi:garage - mdi:garage-open
    #     # mdi:lamp
    #     # mdi:border-all mdi:border-outside
    #     # mdi:lock mdi:lock-open-outline

    #     # mdi-lightbulb
    #     # mdi-lightbulb-on
    #     # mdi-lightbulb-on-outline
    #     # mdi-lightbulb-outline
    #     # mdi-ceiling-light
    #     # mdi-sunglasses
    #     # mdi-fan
    #     # mdi-power-plug
    #     # mdi-power-plug-off
    #     # mdi-speedometer - DIMMER
    #     # mdi-timelapse - DIMMER

    #     # DEVICE_TYPE_LIGHTS, DEVICE_TYPE_COVERS, DEVICE_TYPE_SWITCHES, DEVICE_TYPE_CLIMATES, DEVICE_TYPE_FANS

    #     if device["object_type"] == "CH_Main_Automation":
    #         if device["object_name"].find("VENTILATOR") != -1 or device["object_name"].find(
    #                 "FANCOIL") != -1 or device["object_name"].find("VENTILATORE") != -1:
    #             device_type = DEVICE_TYPE_SWITCHES
    #             device_class = DEVICE_CLASS_SWITCH
    #             icon = ["mdi:fan", "mdi:fan-off"]
    #         elif device["object_name"].find("LAMPE") != -1:
    #             device_type = DEVICE_TYPE_LIGHTS
    #             device_class = DEVICE_CLASS_SWITCH
    #             icon = ["mdi:lightbulb", "mdi:lightbulb-off"]
    #         elif device["object_name"].find("LICHT") != -1:
    #             device_type = DEVICE_TYPE_LIGHTS
    #             icon = "mdi:ceiling-light"
    #         elif device["object_name"].find("STECKDOSE") != -1:
    #             device_type = DEVICE_TYPE_SWITCHES
    #             device_class = DEVICE_CLASS_OUTLET
    #             icon = ["mdi:power-plug", "mdi:power-plug-off"]

    #             # device_type = DEVICE_TYPE_SENSORS
    #             # device_class = DEVICE_CLASS_POWER
    #             # icon = "mdi:home-analytics"

    #         elif device["object_name"].find("PULSANTE") != -1:
    #             device_type = DEVICE_TYPE_SWITCHES
    #             device_class = DEVICE_CLASS_OUTLET
    #             # device_class = "plug"
    #             icon = ["mdi:power-plug", "mdi:power-plug-off"]
    #         else:
    #             # fallback to lights
    #             device_type = DEVICE_TYPE_LIGHTS
    #             icon = "mdi:ceiling-light"

    #     elif device["object_type"] in ["CH_KNX_GENERIC_ONOFF"]:
    #         device_type = DEVICE_TYPE_SWITCHES
    #         device_class = DEVICE_CLASS_OUTLET
    #         icon = ["mdi:power-plug", "mdi:power-plug-off"]

    #     elif device["object_type"] in ["CH_Dimmer_Automation", "CH_Dimmer_RGB", "CH_Dimmer_White", "CH_Dimmer_Hue"]:
    #         device_type = DEVICE_TYPE_LIGHTS
    #         icon = "mdi:speedometer"  # mdi:rotate-right

    #         # device_type = DEVICE_TYPE_SENSORS
    #         # device_class = DEVICE_CLASS_POWER
    #         # icon = "mdi:home-analytics"

    #     elif device["object_type"] in ["CH_ShutterWithoutPosition_Automation", "CH_Shutter_Automation"]:
    #         if device["object_name"].find("F-FERNBEDIENUNG") != -1:
    #             device_type = DEVICE_TYPE_COVERS
    #             device_class = DEVICE_CLASS_WINDOW
    #         else:
    #             # could be: shade, blind, window
    #             # see: https://www.home-assistant.io/integrations/cover/
    #             device_type = DEVICE_TYPE_COVERS
    #             device_class = DEVICE_CLASS_SHUTTER
    #         icon = ["mdi:window-closed", "mdi:window-open"]

    #     elif device["object_type"] in ["CH_Clima", "CH_HVAC_NoZonaNeutra", "CH_Fancoil"]:
    #         device_type = DEVICE_TYPE_CLIMATES
    #         icon = "mdi:thermometer-lines"

    #     elif device["object_type"] == "CH_Scene":
    #         device_type = DEVICE_TYPE_SCENES
    #         device_class = DEVICE_CLASS_SWITCH
    #         icon = "mdi:home-assistant"

    #     elif device["object_type"] in ["CH_Misuratore", "CH_Carichi_Custom", "CH_Carichi", "CH_Carichi_3F"]:
    #         device_type = DEVICE_TYPE_SENSORS
    #         device_class = DEVICE_CLASS_POWER
    #         icon = "mdi:home-analytics"

    #     elif device["object_type"] in ["CH_Audio", "CH_KNX_GENERIC_TIME_S", "CH_SAI", "CH_Event"]:
    #         _LOGGER.debug(
    #             "Unsupported object returned from web server: "
    #             + device["object_type"]
    #             + " / "
    #             + device["object_name"])
    #     else:
    #         _LOGGER.warning(
    #             "Unknown object returned from web server: "
    #             + device["object_type"]
    #             + " / "
    #             + device["object_name"])

    #     return device_type, device_class, icon
