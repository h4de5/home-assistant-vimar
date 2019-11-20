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

ICONS = {"SML": "mdi:run", "RWL": "mdi:ceiling-light", "ZGP": "mdi:lamp"}

# mdi-lightbulb
# mdi-lightbulb-on
# mdi-lightbulb-on-outline
# mdi-lightbulb-outline
# mdi-ceiling-light
# mdi-sunglasses
# mdi-fan
# mdi-power-plug
# mdi-power-plug-off 
# mdi-speedometer - DIMMER
# mdi-timelapse - DIMMER


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Cover platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Cover started!")
    covers = []

    # _LOGGER.info("Vimar Plattform Config: ")
    # _LOGGER.info(config)
    # _LOGGER.info("discovery_info")
    # _LOGGER.info(discovery_info)
    # _LOGGER.info(hass.config)
    # this will give you overall hass config, not configuration.yml
    # hassconfig = hass.config.as_dict()

    # vimarconfig = config

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
        #     covers.append(VimarCover(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            if (device['object_name'].find("ROLLLADEN") != -1 or 
                device['object_name'].find("FERNBEDIENUNG") != -1):
                covers.append(VimarCover(device, device_id, vimarconnection))


    # fallback
    # if len(lights) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             covers.append(VimarCover({'object_name': name}, device_id, link))

    if len(covers) != 0:
        async_add_entities(covers)
    _LOGGER.info("Vimar Cover complete!")

class VimarCover(CoverDevice):
    """ Provides a Vimar cover. """

    # pylint: disable=no-self-use
    def __init__(self, device, device_id, vimarconnection):
        """Initialize the cover."""
        self._device = device
        self._name = self._device['object_name']
        self._device_id = device_id
        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed
        self._state = False
        # _direction = 0 .. upwards
        # _direction = 1 .. downards
        self._direction = 0
        self.reset_status()
        self._vimarconnection = vimarconnection

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return True

    @property
    def should_poll(self):
        """ polling needed for a Vimar cover. """
        return True

    def update(self):
        """Fetch new state data for this cover.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness
        self._device = self._vimarconnection.getDevice(self._device_id)
        self.reset_status()
        
################

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it should be open
        # if its 0, and direction 1, than it was going downwards and it was not stopped, therefor closed
        if self._state :
            return False
        elif self._direction:
            return True
        else:
            return False

    # @property
    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if 'status' in self._device:
            if 'up/down' in self._device['status']:
                self._direction = 1
                self._vimarconnection.updateStatus(self._device['status']['up/down']['status_id'], 1)

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if 'status' in self._device:
            if 'up/down' in self._device['status']:
                self._direction = 0
                self._vimarconnection.updateStatus(self._device['status']['up/down']['status_id'], 0)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if 'status' in self._device:
            if 'stop up/stop down' in self._device['status']:
                self._state = 1
                self._vimarconnection.updateStatus(self._device['status']['stop up/stop down']['status_id'], 1)
        
    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return 'garage'

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    # @property
    # def icon(self):
    #     """Icon to use in the frontend, if any."""
    #     data = self._data.get(self._hue_id)
    #     if data:
    #         icon = ICONS.get(data["model"])
    #         if icon:
    #             return icon
    #     return self.ICON

    def reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device:
            if 'stop up/stop down' in self._device['status']:
                self._state = (False, True)[self._device['status']['stop up/stop down']['status_value'] != '0']
            if 'up/down' in self._device['status']:
                self._direction = int(self._device['status']['up/down']['status_value'])

