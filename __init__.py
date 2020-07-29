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
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .vimarlink import (VimarLink, VimarProject, VimarApiError)

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

                return await hass.async_add_executor_job(vimarproject.update)
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

    if not devices or len(devices) == 0:
        _LOGGER.error("Could not find any devices on Vimar Webserver %s", host)
        return False

    # TODO: rework platform registration
    # according to: https://github.com/home-assistant/core/blob/83d4e5bbb734f77701073710beb74dd6b524195e/homeassistant/helpers/discovery.py#L131
    # https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/__init__.py#L143

    for device_type, platform in AVAILABLE_PLATFORMS.items():
        device_count = vimarproject.platform_exists(device_type)
        if device_count:
            _LOGGER.debug("load platform %s with %d %s", platform, device_count, device_type)
            hass.async_create_task(hass.helpers.discovery.async_load_platform(
                platform, DOMAIN, {"hass_data_key": device_type}, config))

    # States are in the format DOMAIN.OBJECT_ID.
    # hass.states.async_set("vimar_platform.Hello_World", "Works!")

    # Use `listen_platform` to register a callback for these events.
    # homeassistant.helpers.discovery.async_load_platform(hass, component, platform, discovered, hass_config)

    # Return boolean to indicate that initialization was successfully.
    return True
