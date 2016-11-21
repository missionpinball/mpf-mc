"""Contains sound playlist asset classes used by the audio system"""

import logging
import random
import sys
import uuid
from enum import Enum, unique

from mpf.core.assets import Asset, AssetPool
from mpf.core.randomizer import Randomizer
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
        self._type = "sequence"
        self._scope = "player"
        self._fade_in_first_sound = False
        self._fade_out_last_sound = False
        self._events_when_played = None
        self._events_when_stopped = None
        self._events_when_sound_played = None
        self._events_when_sound_stopped = None

        self._sounds = None
        self._machine_wide_dict = dict()

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

        if 'type' in self.config and self.config['type'] is not None:
            self._type = self.config['type']

        if 'scope' in self.config and self.config['scope'] is not None:
            self._scope = self.config['scope']

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

        # self.config['sounds'] contains a list of sounds to include in the playlist.  Optionally,
        # each item in the list can also include an integer weight value delimited by a pipe (|)
        # character.

        # Build list of weighted sound names
        playlist_sounds = list()
        for sound in self.config['sounds']:
            try:
                name, weight = sound.split('|')
                if not weight:
                    weight = 1
                else:
                    weight = int(weight)
            except ValueError:
                name = sound
                weight = 1

            playlist_sounds.append((name, weight))

        self._sounds = playlist_sounds

    @property
    def crossfade_time(self):
        """Return the fade out time for the playlist (in seconds)"""
        return self._crossfade_time

    @property
    def type(self):
        """Return the playlist type"""
        return self._type

    def _get_iterator(self, settings, context, calling_context):
        """
        Returns the playlist iterator/randomizer
        Args:
            settings:
            context:
            calling_context:

        Returns:

        """
        key = "playlist_{}_{}.{}".format(self.name, context, calling_context)
        if self._scope == 'player':
            try:
                playlist_iterator = self.machine.game.player[key]
            except KeyError:
                playlist_iterator = self._create_randomizer()
                self.machine.game.player[key] = playlist_iterator
        else:
            try:
                playlist_iterator = self._machine_wide_dict[key]
            except KeyError:
                playlist_iterator = self._create_randomizer()
                self._machine_wide_dict[key] = playlist_iterator

        return playlist_iterator

    def _create_randomizer(self):
        """Create a randomizer to manage the list of sounds in the playlist"""
        randomizer = Randomizer(self._sounds)

        # Set the randomizer behavior based on the playlist type (random mode)
        if self._type == 'sequence':
            randomizer.disable_random = True
            randomizer.loop = False
            randomizer.force_different = False
            randomizer.force_all = True
        elif self._type == 'random':
            randomizer.disable_random = False
            randomizer.loop = False
            randomizer.force_different = False
            randomizer.force_all = False
        elif self._type == 'random_force_next':
            randomizer.disable_random = False
            randomizer.loop = False
            randomizer.force_different = True
            randomizer.force_all = False
        elif self._type == 'random_force_all':
            randomizer.disable_random = False
            randomizer.loop = False
            randomizer.force_different = True
            randomizer.force_all = True

        return randomizer

    def play(self, settings, context, calling_context, **kwargs):
        """
        Start the playlist playing
        Args:
            settings: Optional dictionary of settings to override the default values.
            context:
            calling_context:
            kwargs:
        Returns:
            A sound instance of the first song to play in the playlist
        """
        self.log.debug("Play playlist %s on track %s", self.name, self._track.name)

        playlist_iterator = self._get_randomizer(settings, context, calling_context)

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