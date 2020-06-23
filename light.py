"""Platform for light integration."""
import logging
from datetime import timedelta

from homeassistant.components.light import ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS

from .const import DOMAIN
from .vimar_entity import VimarEntity

try:
    from homeassistant.components.light import LightEntity
except ImportError:
    from homeassistant.components.light import Light as LightEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)
PARALLEL_UPDATES = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Light platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Light started!")
    lights = []

    vimarconnection = hass.data[DOMAIN]['connection']

    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        for device_id, device in devices.items():
            lights.append(VimarLight(device, device_id, vimarconnection))

    if len(lights) != 0:
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        async_add_entities(lights)
    _LOGGER.info("Vimar Light complete!")


def calculate_brightness(brightness):
    """Scale brightness from 0..255 to 0..100"""
    return round((brightness * 100) / 255)
# end dev calculate_brightness


def recalculate_brightness(brightness):
    """Scale brightness from 0..100 to 0..255"""
    return round((brightness * 255) / 100)
# end dev recalculate_brightness

# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)


class VimarLight(VimarEntity, LightEntity):
    """ Provides a Vimar lights. """

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device
    # assumed_state = False

    # set entity_id, object_id manually due to possible duplicates
    entity_id = "light." + "unset"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the light."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)

        # set device type specific attributes
        self._brightness = 255
        self.entity_id = "light." + self._name.lower() + "_" + self._device_id

    # light properties

    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        if 'status' in self._device and self._device['status']:
            if 'value' in self._device['status']:
                return SUPPORT_BRIGHTNESS
        return 0

    # async getter and setter

    # # def update(self):
    # # see:
    # # https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    # async def async_update(self):
    #     """Fetch new state data for this light.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     # starttime = localtime()
    #     # strftime("%Y-%m-%d %H:%M:%S",
    #     # self._light.update()
    #     # self._state = self._light.is_on()
    #     # self._brightness = self._light.brightness
    #     # self._device = self._vimarconnection.getDevice(self._device_id)
    #     # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
    #     old_status = self._device['status']
    #     self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
    #     self._reset_status()
    #     if old_status != self._device['status']:
    #         self.async_schedule_update_ha_state()
    #     # _LOGGER.debug("Vimar Light update finished after " +
    #     # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    #     # for status_name, status_dict in self._device['status'].items():
    #     #     _LOGGER.info("Vimar light update id: " +
    #     # status_name + " = " + status_dict['status_value'] + " / " +
    #     # status_dict['status_id'])

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar light on. """

        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = True
                self._device['status']['on/off']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                # await
                # self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                # self._device['status']['on/off']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)

        if ATTR_BRIGHTNESS in kwargs:
            if 'status' in self._device and self._device['status']:
                if 'value' in self._device['status']:
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
                    brightness_value = calculate_brightness(self._brightness)
                    self._device['status']['value']['status_value'] = brightness_value
                    # self._vimarconnection.set_device_status(self._device['status']['value']['status_id'], brightness_value)
                    await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value)

        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar light off. """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = False
                self._device['status']['on/off']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 0)

                self.async_schedule_update_ha_state()


    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']
            if 'value' in self._device['status']:
                self._brightness = recalculate_brightness(
                    int(self._device['status']['value']['status_value']))


# end class VimarLight
