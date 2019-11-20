"""Platform for switch integration."""
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.components import switch
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio

# import variables set in __init__.py
# from . import vimarconnection
# from . import vimarlink
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Switch platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Switch started!")
    switches = []

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
        #     switches.append(VimarSwitch(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            if device['object_name'].find("STECKDOSE") != -1:
                switches.append(VimarSwitch(device, device_id, vimarconnection))


    # fallback
    # if len(switches) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             switches.append(VimarSwitch({'object_name': name}, device_id, link))

    if len(switches) != 0:
        async_add_entities(switches)
    _LOGGER.info("Vimar Switch complete!")


def calculate_brightness(brightness):
    """Scale brightness from 0..255 to 0..100"""
    return round((brightness * 100) / 255)
# end dev calculate_brightness

def recalculate_brightness(brightness):
    """Scale brightness from 0..100 to 0..255"""
    return round((brightness * 255) / 100)
# end dev recalculate_brightness





class VimarSwitch(ToggleEntity):
    """ Provides a Vimar switches. """

    ICON = "mdi:power-plug"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the switch."""
        self._device = device
        self._name = self._device['object_name']
        self._device_id = device_id
        self._state = False
        self.reset_status()
        self._vimarconnection = vimarconnection

    # @property
    # def supported_features(self):
    #     """Flag supported features."""
    #     if 'status' in self._device:
    #         if 'value' in self._device['status']:
    #             return SUPPORT_BRIGHTNESS
    #     return None

    @property
    def should_poll(self):
        """ polling needed for a Vimar switch. """
        return True

    def update(self):
        """Fetch new state data for this switch.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._device = self._vimarconnection.getDevice(self._device_id)
        self.reset_status()
        
    @property
    def name(self):
        """ Returns the name of the switch. """
        return self._name

    @property
    def is_on(self):
        """ True if the SwitchWave switch is on. """
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        # return ICON
        return self.ICON

    def reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[self._device['status']['on/off']['status_value'] != '0']
            

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar switch on. """
        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = True
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], 1)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar switch off. """
        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = False
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], 0)

        self.async_schedule_update_ha_state()

        