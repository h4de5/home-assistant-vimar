"""Platform for light integration."""

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
import homeassistant.util.color as color_util

from .const import DEVICE_TYPE_LIGHTS as CURR_PLATFORM
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Light platform."""
    vimar_setup_entry(VimarLight, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarLight(VimarEntity, LightEntity):
    """Provides a Vimar lights."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the light."""
        VimarEntity.__init__(self, coordinator, device_id)

        # self.entity_id = "light." + self._name.lower() + "_" + self._device_id

    # light properties

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    @property
    def is_on(self) -> bool:
        """Set to True if the device is on."""
        return self.get_state("on/off") == "1"

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return self.is_on

    @property
    def brightness(self):
        """Return Brightness of this light between 0..255."""
        return self.recalculate_brightness(int(self.get_state("value") or 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB colors."""
        return (
            self.get_state("red") or 0,
            self.get_state("green") or 0,
            self.get_state("blue") or 0,
        )

    @property
    def hs_color(self):
        """Return the hue and saturation."""
        return color_util.color_RGB_to_hs(*self.rgb_color)

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        if self.has_state("red") and self.has_state("green") and self.has_state("blue"):
            return ColorMode.RGB
        if self.has_state("value"):
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode] | None:
        """Flag supported color modes."""
        flags: set[ColorMode] = set()

        if self.has_state("red") and self.has_state("green") and self.has_state("blue"):
            flags.add(ColorMode.RGB)
            # flags.add(ColorMode.HS)
        elif self.has_state("value"):
            flags.add(ColorMode.BRIGHTNESS)
        else:
            flags.add(ColorMode.ONOFF)

        return flags

    # async getter and setter

    async def async_turn_on(self, **kwargs):
        """Turn the Vimar light on."""
        if not kwargs:
            self.change_state("on/off", "1")
        else:
            if ATTR_BRIGHTNESS in kwargs and self.has_state("value"):
                brightness_value = self.calculate_brightness(kwargs[ATTR_BRIGHTNESS])
                self.change_state(
                    "value",
                    brightness_value,
                    "on/off",
                    ("0", "1")[brightness_value > 0],
                )

            if ATTR_HS_COLOR in kwargs and self.has_state("red"):
                rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
                self.change_state("red", rgb[0], "green", rgb[1], "blue", rgb[2])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the Vimar light off."""
        self.change_state("on/off", "0")

    def calculate_brightness(self, brightness):
        """Scale brightness from 0..255 to 0..100."""
        return round((brightness * 100) / 255)

    def recalculate_brightness(self, brightness):
        """Scale brightness from 0..100 to 0..255."""
        return round((brightness * 255) / 100)


# end class VimarLight
