"""Contains sound playlist asset classes used by the audio system"""

import logging
import random
import sys
import uuid
from enum import Enum, unique

from mpf.core.assets import Asset, AssetPool
from mpf.core.utility_functions import Util
from mpfmc.core.audio.audio_interface import AudioInterface, AudioException

class PlaylistAsset(Asset):
    """
    Sound asset class contains a single sound that may be played using the audio engine.

    Notes:
        It is critical that the AudioInterface be initialized before any Sound assets
        are loaded.  The loading code relies upon having an active audio interface.
    """
    attribute = 'playlists'  # attribute in MC, e.g. self.mc.images
    path_string = 'playlists'  # entry from mpf_mc:paths: for asset folder name
    config_section = 'playlists'  # section in the config files for this asset
    extensions = None  # Additional extensions may be added at runtime
    class_priority = 99  # Order asset classes will be loaded. Higher is first.
    pool_config_section = None  # Will setup groups if present
    asset_group_class = None  # Class or None to not use pools

    # pylint: disable=too-many-branches, too-many-statements, invalid-name
    def __init__(self, mc, name, file, config):
        """ Constructor"""
        super().__init__(mc, name, file, config)

        self._track = None
        self.log = logging.getLogger('PlaylistAsset')
        self._track = None
        self._crossfade_time = 0.0
        self._random = False
        self._fade_in_first_sound = False
        self._fade_out_last_sound = False
        self._events_when_played = None
        self._events_when_stopped = None
        self._events_when_sound_played = None
        self._events_when_sound_stopped = None

        self._sounds = list()
        self._sounds_played = set()
        self._last_sound = None

        # Make sure a legal track name has been specified (unless only one track exists)
        if 'track' not in self.config:
            # Track not specified
            self.log.error("Playlist must have a valid track name. "
                           "Could not create playlist '%s' asset.", name)
            raise AudioException("Sound must have a valid track name. "
                                 "Could not create sound '{}' asset".format(name))
        else:
            # Track specified in config, validate it
            track = self.machine.sound_system.audio_interface.get_track_by_name(
                self.config['track'])
            if track is None:
                self.log.error("'%s' is not a valid track name. "
                               "Could not create sound '%s' asset.", self.config['track'], name)
                raise AudioException("'{}' is not a valid track name. "
                                     "Could not create sound '{}' asset"
                                     .format(self.config['track'], name))

        self._track = track

        if 'crossfade_time' in self.config and self.config['crossfade_time'] is not None:
            self._crossfade_time = Util.string_to_secs(self.config['crossfade_time'])

        if 'events_when_played' in self.config and isinstance(
                self.config['events_when_played'], str):
            self._events_when_played = Util.string_to_list(self.config['events_when_played'])

        if 'events_when_stopped' in self.config and isinstance(
                self.config['events_when_stopped'], str):
            self._events_when_stopped = Util.string_to_list(self.config['events_when_stopped'])

        if 'events_when_sound_played' in self.config and isinstance(
                self.config['events_when_sound_played'], str):
            self._events_when_sound_played = Util.string_to_list(self.config['events_when_sound_played'])

        if 'events_when_sound_stopped' in self.config and isinstance(
                self.config['events_when_sound_stopped'], str):
            self._events_when_sound_stopped = Util.string_to_list(self.config['events_when_sound_stopped'])

        if 'sounds' not in self.config or self.config['sounds'] is None:
            self.log.error("A playlist must contain at least one sound. "
                           "Could not create playlist '%s' asset.", name)
            raise AudioException("A playlist must contain at least one sound. "
                                 "Could not create playlist '{}' asset.".format(name))

    @property
    def crossfade_time(self):
        """Return the fade out time for the playlist (in seconds)"""
        return self._crossfade_time

    @property
    def random(self):
        """Return whether or not the playlist order is random"""
        return self._random

    def play(self, settings=None):
        """
        Start the playlist playing
        Args:
            settings: Optional dictionary of settings to override the default values.
        Returns:
            A sound instance of the first song to play in the playlist
        """
        self.log.debug("Play playlist %s on track %s", self.name, self._track.name)


        return self._track.play_playlist(self)

    def stop(self):
        """Stop playing the current playlist"""
        pass

    def next_sound(self):
        """
        Advance the playlist to the next sound in the list
        Returns:
            A sound instance of the next song to play in the playlist or None if there are no
            more songs in the playlist.
        """
        pass

    def _get_next_sound(self):
        """Return the next sound to play from the playlist."""

        if len(self._sounds) == 1:
            return self._sounds[0]

        # Check if all sounds have been played
        if len(self._sounds_played) == len(self._sounds):
            self._sounds_played = set()

        if self._random:
            choices = [x for x in self._sounds if x not in self._sounds_played and x is not self._last_sound]
            value = random.randint(0, len(choices) - 1)
            return choices[value]
        else:
            return self._sounds[len(self._sounds_played)]

    def reset(self):
        self._sounds_played = set()