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
    CONF_GLOBAL_CHANNEL_ID,
    CONF_IGNORE_PLATFORM,
    DEFAULT_USERNAME,
    DEFAULT_SCHEMA,
    DEFAULT_PORT,
    DEFAULT_CERTIFICATE,
    DEFAULT_TIMEOUT,
    DEVICE_TYPE_LIGHTS,
    DEVICE_TYPE_COVERS,
    DEVICE_TYPE_SWITCHES,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_MEDIA_PLAYERS,
    DEVICE_TYPE_SCENES,
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
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Range(min=2, max=60),
        vol.Optional(CONF_GLOBAL_CHANNEL_ID): vol.Range(min=1, max=99999),
        vol.Optional(CONF_IGNORE_PLATFORM, default=[]): vol.All(cv.ensure_list, [cv.string])
    })
}, extra=vol.ALLOW_EXTRA)

AVAILABLE_PLATFORMS = {
    DEVICE_TYPE_LIGHTS: 'light',
    DEVICE_TYPE_COVERS: 'cover',
    DEVICE_TYPE_SWITCHES: 'switch',
    DEVICE_TYPE_CLIMATES: 'climate',
    DEVICE_TYPE_MEDIA_PLAYERS: 'media_player',
    DEVICE_TYPE_SCENES: 'scene',
    # DEVICE_TYPE_FANS: 'fan',
    DEVICE_TYPE_SENSORS: 'sensor',
    # DEVICE_TYPE_OTHERS: ''
}


@asyncio.coroutine
async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Connect to the Vimar Webserver, verify login and read all devices."""
    devices = {}
    vimarconfig = config[DOMAIN]

    vimarproject, vimarconnection = await _validate_vimar_credentials(hass, vimarconfig)

    # save vimar connection into hass data to share it with other platforms
    hass.data.setdefault(DOMAIN, {})
    # hass.data[DOMAIN] = {}
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
    # _LOGGER.debug("calling refresh..")
    await coordinator.async_refresh()
    # _LOGGER.debug("done refresh")

    devices = coordinator.data

    if not devices or len(devices) == 0:
        # _LOGGER.error("Could not find any devices on Vimar Webserver %s", host)
        _LOGGER.error("Could not find any devices on Vimar Webserver")
        return False

    # TODO: rework platform registration
    # according to: https://github.com/home-assistant/core/blob/83d4e5bbb734f77701073710beb74dd6b524195e/homeassistant/helpers/discovery.py#L131
    # https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/__init__.py#L143

    ignored_platforms = vimarconfig.get(CONF_IGNORE_PLATFORM)

    for device_type, platform in AVAILABLE_PLATFORMS.items():
        if (not ignored_platforms or not platform in ignored_platforms):
            device_count = vimarproject.platform_exists(device_type)
            if device_count:
                _LOGGER.debug("load platform %s with %d %s", platform, device_count, device_type)
                hass.async_create_task(hass.helpers.discovery.async_load_platform(
                    platform, DOMAIN, {"hass_data_key": device_type}, config))
        else:
            _LOGGER.warning('ignore platform: %s', platform)

    # States are in the format DOMAIN.OBJECT_ID.
    # hass.states.async_set("vimar_platform.Hello_World", "Works!")

    # Use `listen_platform` to register a callback for these events.
    # homeassistant.helpers.discovery.async_load_platform(hass, component, platform, discovered, hass_config)

    # Return boolean to indicate that initialization was successfully.
    return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Set up vimar from a config entry."""
#     hass.data[DOMAIN][entry.entry_id] = hub.Hub(hass, entry.data["host"])

#     # This creates each HA object for each platform your device requires.
#     # It's done by calling the `async_setup_entry` function in each platform module.
#     for component in PLATFORMS:
#         hass.async_create_task(
#             hass.config_entries.async_forward_entry_setup(entry, component)
#         )

#     return True


async def _validate_vimar_credentials(hass: HomeAssistantType, vimarconfig: ConfigType) -> [VimarProject, VimarLink]:
    """Validate Vimar credential config."""
    # vimar_config = vimarconfig.copy()
    # del vimar_config[CONF_NAME]
    # del vimar_config[CONF_VALIDATE]

    schema = vimarconfig.get(CONF_SCHEMA)
    host = vimarconfig.get(CONF_HOST)
    port = vimarconfig.get(CONF_PORT)
    username = vimarconfig.get(CONF_USERNAME)
    password = vimarconfig.get(CONF_PASSWORD)
    certificate = vimarconfig.get(CONF_CERTIFICATE)
    timeout = vimarconfig.get(CONF_TIMEOUT)
    global_channel_id = vimarconfig.get(CONF_GLOBAL_CHANNEL_ID)
    # ignored_platforms = vimarconfig.get(CONF_IGNORE_PLATFORM)

    # initialize a new VimarLink object
    vimarconnection = VimarLink(
        schema, host, port, username, password, certificate, timeout)

    # will hold all the devices and their states
    vimarproject = VimarProject(vimarconnection)

    if global_channel_id is not None:
        vimarproject.global_channel_id = global_channel_id

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

    return [vimarproject, vimarconnection]

    # # profile = aws_config.get(CONF_PROFILE_NAME)

    # if profile is not None:
    #     session = aiobotocore.AioSession(profile=profile)
    #     del aws_config[CONF_PROFILE_NAME]
    #     if CONF_ACCESS_KEY_ID in aws_config:
    #         del aws_config[CONF_ACCESS_KEY_ID]
    #     if CONF_SECRET_ACCESS_KEY in aws_config:
    #         del aws_config[CONF_SECRET_ACCESS_KEY]
    # else:
    #     session = aiobotocore.AioSession()

    # if credential[CONF_VALIDATE]:
    #     async with session.create_client("iam", **aws_config) as client:
    #         await client.get_user()
    # return session
