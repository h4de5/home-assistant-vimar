"""Platform for light integration."""
import logging

# from datetime import timedelta
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_HS_COLOR, SUPPORT_BRIGHTNESS, SUPPORT_COLOR)
import homeassistant.util.color as color_util

# from .const import DOMAIN
from .vimar_entity import (VimarEntity, vimar_setup_platform)

try:
    from homeassistant.components.light import LightEntity
except ImportError:
    from homeassistant.components.light import Light as LightEntity

_LOGGER = logging.getLogger(__name__)


# SCAN_INTERVAL = timedelta(seconds=30)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)
# PARALLEL_UPDATES = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Light platform."""
    vimar_setup_platform(VimarLight, hass, async_add_entities, discovery_info)


# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)


class VimarLight(VimarEntity, LightEntity):
    """Provides a Vimar lights."""

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device
    # assumed_state = False

    # _platform = "light"
    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "light." + "unset"
    _brightness = None
    _red = None
    _blue = None
    _green = None

    def __init__(self, device_id, vimarconnection, vimarproject, coordinator):
        """Initialize the light."""
        # LightEntity.__init__()
        VimarEntity.__init__(self, device_id, vimarconnection, vimarproject, coordinator)

        # set device type specific attributes
        # self._brightness = 255
        # self.entity_id = "light." + self._name.lower() + "_" + self._device_id

    # light properties

    @property
    def is_on(self):
        """Set to True if the device is on."""
        return self.get_state('on/off') == '1'

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return self.is_on

    @property
    def brightness(self):
        """Return Brightness of this light between 0..255."""
        # return self._brightness
        return self.recalculate_brightness(int(self.get_state('value')))

    @property
    def rgb_color(self):
        """Return RGB colors."""
        return (self._red, self._green, self._blue)

    @property
    def hs_color(self):
        """Return the hue and saturation."""
        return color_util.color_RGB_to_hs(*self.rgb_color)

    @property
    def supported_features(self):
        """Flag supported features."""
        flags = 0
        if 'status' in self._device and self._device['status']:
            if 'value' in self._device['status']:
                flags |= SUPPORT_BRIGHTNESS
            if 'red' in self._device['status']:
                flags |= SUPPORT_COLOR
        return flags

    # async getter and setter

    async def async_turn_on(self, **kwargs):
        """Turn the Vimar light on."""
        if not kwargs:
            self.change_state('on/off', '1')
        else:
            if ATTR_BRIGHTNESS in kwargs and 'value' in self._device['status']:
                brightness_value = self.calculate_brightness(kwargs[ATTR_BRIGHTNESS])
                self.change_state('value', brightness_value, 'on/off', ('0', '1')[brightness_value > 0])

            if ATTR_HS_COLOR in kwargs and 'red' in self._device['status']:
                rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
                self.change_state('red', rgb[0], 'green', rgb[1], 'blue', rgb[2])

                # self._red = rgb[0]
                # self._green = rgb[1]
                # self._blue = rgb[2]

                # self._device['status']['red']['status_value'] = self._red
                # self._device['status']['green']['status_value'] = self._green
                # self._device['status']['blue']['status_value'] = self._blue

                # await asyncio.gather(
                #     self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['red']['status_id'], self._red),
                #     self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['green']['status_id'], self._green),
                #     self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['blue']['status_id'], self._blue)
                # )

                # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['red']['status_id'], self._red)
                # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['status']['status_id'], self._green)
                # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['blue']['status_id'], self._blue)

        # self.request_statemachine_update()

    async def async_turn_off(self):
        """Turn the Vimar light off."""
        self.change_state('on/off', '0')

    # private helper methods
#     def _reset_status(self):
#         """Set status from _device to class variables."""
#         if 'status' in self._device and self._device['status']:
#             if 'on/off' in self._device['status']:
#                 self._state = (False, True)[
#                     self._device['status']['on/off']['status_value'] != '0']
#             if 'value' in self._device['status']:
#                 self._brightness = self.recalculate_brightness(
#                     int(self._device['status']['value']['status_value']))
# # Row000074: '19758','on/off','-1','0'
# # Row000075: '19762','control_dimming','-1','0'
# # Row000076: '19764','direction_dimming','-1','0'
# # Row000077: '19766','on/off','-1','1'
# # Row000078: '19768','red','-1','255'
# # Row000079: '19769','green','-1','0'
# # Row000080: '19770','blue','-1','90'
# # Row000081: '19774', 'on/off fadingshow', '-1', '1'
#             if 'red' in self._device['status']:
#                 self._red = int(self._device['status']['red']['status_value'])
#             if 'blue' in self._device['status']:
#                 self._blue = int(self._device['status']['blue']['status_value'])
#             if 'green' in self._device['status']:
#                 self._green = int(self._device['status']['green']['status_value'])

    def calculate_brightness(self, brightness):
        """Scale brightness from 0..255 to 0..100."""
        return round((brightness * 100) / 255)
    # end dev calculate_brightness

    def recalculate_brightness(self, brightness):
        """Scale brightness from 0..100 to 0..255."""
        return round((brightness * 255) / 100)
    # end dev recalculate_brightness


# end class VimarLight
