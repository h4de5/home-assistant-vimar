"""Platform for light integration."""
import logging
from datetime import timedelta

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_HS_COLOR, SUPPORT_BRIGHTNESS, SUPPORT_COLOR)
import homeassistant.util.color as color_util
import asyncio

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


# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)


class VimarLight(VimarEntity, LightEntity):
    """ Provides a Vimar lights. """

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device
    # assumed_state = False

    # set entity_id, object_id manually due to possible duplicates
    entity_id = "light." + "unset"
    _brightness = None
    _red = None
    _blue = None
    _green = None

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the light."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)

        # set device type specific attributes
        # self._brightness = 255
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
    def rgb_color(self):
        """Return RGB colors"""
        return (self._red, self._green, self._blue)

    @property
    def hs_color(self):
        """Return the hue and saturation."""
        return color_util.color_RGB_to_hs(*self.rgb_color())

    @property
    def supported_features(self):
        """Flag supported features."""
        flags = 0
        if 'status' in self._device and self._device['status']:
            if 'value' in self._device['status']:
                flags |= SUPPORT_BRIGHTNESS
        if 'status' in self._device and self._device['status']:
            if 'red' in self._device['status']:
                flags |= SUPPORT_COLOR
        return flags

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
            if not kwargs:
                if 'on/off' in self._device['status']:
                    self._state = True
                    self._device['status']['on/off']['status_value'] = '1'
                    # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                    # await
                    # self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                    # self._device['status']['on/off']['status_id'], 1)
                    await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
            else:
                if ATTR_BRIGHTNESS in kwargs and 'value' in self._device['status']:
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
                    brightness_value = self.calculate_brightness(self._brightness)
                    self._device['status']['value']['status_value'] = brightness_value

                    if 'on/off' in self._device['status']:
                        if brightness_value > 0:
                            self._state = True
                            self._device['status']['on/off']['status_value'] = '1'
                        else:
                            self._state = False
                            self._device['status']['on/off']['status_value'] = '0'

                    # self._vimarconnection.set_device_status(self._device['status']['value']['status_id'], brightness_value)
                    # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value)
                    await asyncio.gather(
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value),
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], (0, 1)[self._state])
                    )

                if ATTR_HS_COLOR in kwargs and 'red' in self._device['status']:

                    rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])

                    self._red = rgb[0]
                    self._green = rgb[1]
                    self._blue = rgb[2]

                    self._device['status']['red']['status_value'] = self._red
                    self._device['status']['green']['status_value'] = self._green
                    self._device['status']['blue']['status_value'] = self._blue

                    await asyncio.gather(
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['red']['status_id'], self._red),
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['green']['status_id'], self._green),
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['blue']['status_id'], self._blue)
                    )

                    # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['red']['status_id'], self._red)
                    # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['status']['status_id'], self._green)
                    # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['blue']['status_id'], self._blue)

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
                self._brightness = self.recalculate_brightness(
                    int(self._device['status']['value']['status_value']))
# Row000074: '19758','on/off','-1','0'
# Row000075: '19762','control_dimming','-1','0'
# Row000076: '19764','direction_dimming','-1','0'
# Row000077: '19766','on/off','-1','1'
# Row000078: '19768','red','-1','255'
# Row000079: '19769','green','-1','0'
# Row000080: '19770','blue','-1','90'
# Row000081: '19774', 'on/off fadingshow', '-1', '1'
            if 'red' in self._device['status']:
                self._red = int(self._device['status']['red']['status_value'])
            if 'blue' in self._device['status']:
                self._blue = int(self._device['status']['blue']['status_value'])
            if 'green' in self._device['status']:
                self._green = int(self._device['status']['green']['status_value'])

    def calculate_brightness(self, brightness):
        """Scale brightness from 0..255 to 0..100"""
        return round((brightness * 100) / 255)
    # end dev calculate_brightness

    def recalculate_brightness(self, brightness):
        """Scale brightness from 0..100 to 0..255"""
        return round((brightness * 255) / 100)
    # end dev recalculate_brightness


# end class VimarLight
