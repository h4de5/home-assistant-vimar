"""Platform for cover integration."""
# credits to https://community.home-assistant.io/t/create-new-cover-component-not-working/50361/5

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP)


from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
)

from homeassistant.const import (
    CONF_COVERS, CONF_DEVICE, STATE_CLOSED, STATE_OPEN, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
from . import DOMAIN


_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neocontroller'

CONF_DEVICE_ID = 'device_id'

STATE_CLOSING = 'closing'
STATE_OFFLINE = 'offline'
STATE_OPENING = 'opening'
STATE_STOPPED = 'stopped'

COVER_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_ID): cv.string,
    vol.Required(CONF_CODE): cv.string
})

blindDown = 'http://{}:8838/neo/v1/transmit?command={}-dn&id={}'
blindUp = 'http://{}:8838/neo/v1/transmit?command={}-up&id={}'
blindStop = 'http://{}:8838/neo/v1/transmit?command={}-sp&id={}'

############

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Light platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Light started!")
    lights = []

    # _LOGGER.info("Vimar Plattform Config: ")
    # _LOGGER.info(config)
    _LOGGER.info("discovery_info")
    _LOGGER.info(discovery_info)
    # _LOGGER.info(hass.config)
    # this will give you overall hass config, not configuration.yml
    # hassconfig = hass.config.as_dict()

    # vimarconfig = config

    # _LOGGER.info(vimarconfig)

    # host = vimarconfig.get(CONF_HOST)
    # username = vimarconfig.get(CONF_USERNAME)
    # password = vimarconfig.get(CONF_PASSWORD)

    # vimarconnection = vimarlink.VimarLink(host, username, password)

    # # Verify that passed in configuration works
    # if not vimarconnection.is_valid_login():
    #     _LOGGER.error("Could not connect to Vimar Webserver "+ host)
    #     return False

    # _LOGGER.info(config)
    vimarconnection = hass.data[DOMAIN]
    
    # load Main Groups
    vimarconnection.getMainGroups()

    # load devices
    devices = vimarconnection.getDevices()

    if len(devices) != 0:
        # for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        # for device_id, device_config in devices.items():
        #     name = device_config['name']
        #     lights.append(VimarLight(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            lights.append(VimarLight(device, device_id, vimarconnection))


    # fallback
    if len(lights) == 0:
        # Config is empty so generate a default set of switches
        for room in range(1, 2):
            for device in range(1, 2):
                name = "Room " + str(room) + " Device " + str(device)
                device_id = "R" + str(room) + "D" + str(device)
                lights.append(VimarLight({'object_name': name}, device_id, link))

    async_add_entities(lights)
    _LOGGER.info("Vimar Light complete!")




class VimarCover(CoverDevice):
    """Representation of NeoController cover."""

    # pylint: disable=no-self-use
    def __init__(self, hass, args):
        """Initialize the cover."""
        self.hass = hass
        self._name = args[CONF_NAME]
        self.device_id = args['device_id']
        self._ip_addr = args[CONF_IP_ADDRESS]
        self._id      = args[CONF_ID]
        self._code    = args[CONF_CODE]
        self._available = True
        self._state = None

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available
        
################

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._state in [STATE_UNKNOWN, STATE_OFFLINE]:
            return None
        return self._state in [STATE_CLOSED, STATE_OPENING]

    @property
    def close_cover(self):
        """Close the cover."""
        requests.get(blindDown.format(self._ip_addr, self._code, self._id))

    def open_cover(self):
        """Open the cover."""
        requests.get(blindUp.format(self._ip_addr, self._code, self._id))

    def stop_cover(self):
        """Stop the cover."""
        requests.get(blindStop.format(self._ip_addr, self._code, self._id))
        
    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return 'garage'

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
