"""Platform for media player integration."""

import logging

from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_MUSIC,
    SUPPORT_NEXT_TRACK,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import STATE_OFF, STATE_PLAYING  # STATE_IDLE,

from .vimar_entity import VimarEntity, vimar_setup_entry

try:
    from homeassistant.components.media_player import MediaPlayerEntity
except ImportError:
    from homeassistant.components.media_player import MediaPlayerDevice as MediaPlayerEntity

from .const import DEVICE_TYPE_MEDIA_PLAYERS as CURR_PLATFORM

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Mediaplayer platform."""
    vimar_setup_entry(VimarMediaplayer, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarMediaplayer(VimarEntity, MediaPlayerEntity):
    """Provide Vimar media player."""

    _last_volume = 0.1
    _channel_source_id = 0
    _global_channel_id = 1545

    # bus attributes, documentation and home-assistant have different
    # wordings for source and channel
    # vimar can only do next track (0), and next channel (1)
    # bus       | doc       | hass
    # ----------------------------
    # channel   | channel   | source
    # source    | track     | channel

    def __init__(self, coordinator, device_id: int):
        """Initialize the media players."""
        VimarEntity.__init__(self, coordinator, device_id)

        # self.entity_id = "media_player." + self._name.lower() + "_" + self._device_id

        # CH_Audio somehow uses a global status id for all radios
        if coordinator.vimarproject.global_channel_id is not None:
            self._global_channel_id = coordinator.vimarproject.global_channel_id
            self._device["status"]["global_channel"] = {
                "status_id": str(self._global_channel_id),
                "status_value": "0",
                "status_range": "0-7",
            }

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    # media player properties
    @property
    def state(self):
        """State of the player."""
        if self.is_on:
            return STATE_PLAYING
        else:
            return STATE_OFF

    @property
    def is_on(self):
        """Return True if the device is on."""
        # _LOGGER.info("Vimar media player is_on: %s", self.get_state('on/off') == '1')
        return self.get_state("on/off") == "1"

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self.has_state("volume"):
            return float(self.get_state("volume")) / 100

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        if self.has_state("volume"):
            return float(self.get_state("volume")) == 0

    @property
    def media_channel(self):
        """Channel currently playing."""
        if self.has_state("source"):
            return self.get_state("source")
        # if self.has_state('channel'):
        #     return self.get_state('channel')
        else:
            return 0

    @property
    def source(self):
        """Name of the current input source."""
        # if self.has_state('source'):
        #     return self.get_state('source')
        if self.has_state("channel"):
            return self.get_state("channel")
        else:
            return None
            # if self.get_state('source') == 4:
            #     return "Source " + self.get_state('source') + ": Radio"
            # else:
            #     return "Source " + self.get_state('source')

    @property
    def source_list(self):
        """List of available input sources."""
        # return {'1': 'Source 1', '2': 'Source 2', '3': 'Source 3', '4': 'Source 4 - Radio'}
        return ["0", "1", "2", "3", "4", "5", "6", "7", "8"]

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        # if self.has_state('source') and self.get_state('source') == self._channel_source_id:
        if self.has_state("channel") and self.get_state("channel") == self._channel_source_id:
            return MEDIA_TYPE_CHANNEL
        else:
            return MEDIA_TYPE_MUSIC

    @property
    def media_title(self):
        """Title of current playing media."""
        play = "Playing"
        # if self.has_state('source'):
        if self.has_state("channel"):
            play += " source: " + self.get_state("channel")
        if self.has_state("source"):
            play += " channel: " + self.get_state("source")
        return play

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return (self.is_on, True)[self.is_on is None]

    # 'channel': {'status_id': '2536', 'status_value': '0'},
    # 'on/off': {'status_id': '2553', 'status_value': '0'},
    # 'volume': {'status_id': '2561', 'status_value': '100'},
    # 'source': {'status_id': '2562', 'status_value': '4'}

    @property
    def supported_features(self):
        """Flag supported features."""
        flags = 0
        if self.has_state("on/off"):
            flags |= SUPPORT_TURN_ON | SUPPORT_TURN_OFF
        if self.has_state("volume"):
            flags |= SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_STEP
        # if self.has_state('source'):
        if self.has_state("channel"):
            flags |= SUPPORT_SELECT_SOURCE
            # channel only available on source == 0 /
            # if self.get_state('source') == 0 and self.has_state('channel'):
            # if self.get_state('channel') == self._channel_source_id and self.has_state('source'):
            #     flags |= SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK
        # allow  channel change all the time
        if self.has_state("source"):
            # we can only do next track
            # flags |= SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK
            flags |= SUPPORT_NEXT_TRACK

        # FIXED FIX ME - remove me in live
        # flags |= SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_SELECT_SOURCE | SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK

        return flags

    # async getter and setter
    async def async_mute_volume(self, mute):
        """Mute the volume."""
        if mute:
            self._last_volume = self.volume_level
            self.change_state("volume", 0)
        else:
            self.change_state("volume", str(int(self._last_volume * 100)))

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self.change_state("volume", str(int(volume * 100)))

    async def async_media_next_track(self):
        """Send next track command."""
        channel = int(self.media_channel) + 1
        if channel > 8:
            channel = 0
        _LOGGER.debug("Vimar media player setting next channel: %d", channel)
        self.change_state("source", str(channel))
        if self.has_state("global_channel"):
            _LOGGER.info("Vimar media player setting global channel: %d", channel)
            # self.change_state('global_channel', str(channel))
            # according to docs, choosing next track, needs to send 0
            self.change_state("global_channel", "0")

    # no longer available
    async def async_media_previous_track(self):
        """Send previous track command."""
        channel = int(self.media_channel) - 1
        if channel < 0:
            channel = 8
        _LOGGER.info("Vimar media player setting previous channel: %d", channel)
        self.change_state("source", str(channel))
        if self.has_state("global_channel"):
            _LOGGER.info("Vimar media player setting global channel: %d", channel)
            self.change_state("global_channel", str(channel))

    async def async_select_source(self, source):
        """Select input source."""
        _LOGGER.debug("Vimar media player setting source: %s", source)
        # self.change_state('source', str(source))
        self.change_state("channel", str(source))
        # according to docs, choosing next channel, needs to send 1
        self.change_state("global_channel", "1")

    # def turn_on(self):
    #     """Turn the Vimar media player on."""
    #     _LOGGER.info("Vimar media player setting on 2")
    #     self.change_state('on/off', '1')

    async def async_turn_on(self):
        """Turn the Vimar media player on."""
        _LOGGER.debug("Vimar media player setting on")
        self.change_state("on/off", "1")

    async def async_turn_off(self):
        """Turn the Vimar media player off."""
        # if self.has_state('on/off'):
        _LOGGER.debug("Vimar media player setting off")
        self.change_state("on/off", "0")

    async def async_media_stop(self):
        """Send stop command."""
        _LOGGER.debug("Vimar media player setting off via stop button")
        self.change_state("on/off", "0")


# end class VimarMediaplayer
