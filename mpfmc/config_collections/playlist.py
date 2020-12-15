from enum import Enum, unique
from typing import Optional

from mpf.core.randomizer import Randomizer
from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.config_collection import ConfigCollection


class PlaylistCollection(ConfigCollection):

    config_section = 'playlists'
    collection = 'playlists'
    class_label = 'Playlists'

    def __init__(self, mc, collection, config_section):
        super().__init__(mc, collection, config_section)

        self._validate_handler = None

    def create_entries(self, config: dict, **kwargs) -> None:
        # Do not call base class implementation
        del kwargs

        # Loop over items in the config (localized to this collection's section)
        for name, settings in config.items():
            try:
                self[name] = self.process_config(settings)
            except (AudioException, ValueError) as ex:
                raise ValueError("An error occurred while processing the '{}' entry in "
                                 "the playlists config collection: {}".format(name, ex))

        # Validation of referenced sound assets must be completed after all
        # assets have been loaded (can use the init_done event for that)
        self._validate_handler = self.mc.events.add_handler("init_done", self._validate_sound_assets)

    def process_config(self, config: dict) -> dict:
        # processes the 'playlists' section of a config file to populate the
        # mc.playlists dict.

        # config is localized to 'playlists' section
        return self.process_playlist(config)

    def process_playlist(self, config: dict) -> dict:
        # config is localized to a single playlist settings within a list

        self.mc.config_validator.validate_config('playlists', config)

        # Clamp volume between 0 and 1
        if 'volume' in config and config['volume']:
            if config['volume'] < 0:
                config['volume'] = 0
            elif config['volume'] > 1:
                config['volume'] = 1

        return config

    def _validate_sound_assets(self, **kwargs) -> None:
        """Validate the referenced sound assets in the playlist.

        Notes:
            This must be performed after all the sound assets have been loaded.
        """
        del kwargs
        if self._validate_handler:
            self.mc.events.remove_handler(self._validate_handler)

        # bail out if there is no sound system
        if not hasattr(self.mc, "sounds"):
            return

        for name, config in self.items():
            # Validate sound settings in sounds (make sure only valid sound assets are referenced and
            # at least one sound is referenced)
            if not config["sounds"]:
                raise ValueError("The '{}' playlist does not contain any sound assets in "
                                 "its sound: section".format(name))

            for sound in config["sounds"]:
                if sound not in self.mc.sounds:
                    raise ValueError("The '{}' playlist references an invalid sound asset "
                                     "name '{}' in one of its layers".format(name, sound))


# ---------------------------------------------------------------------------
#    PlaylistInstanceStatus class
# ---------------------------------------------------------------------------
@unique
class PlaylistInstanceStatus(Enum):
    """Enumerated class containing status values for PlayfieldInstance class."""
    pending = 0
    playing = 2
    stopping = 3
    finished = 4


# ---------------------------------------------------------------------------
#    PlaylistInstance class
# ---------------------------------------------------------------------------
# pylint: disable=too-many-public-methods
class PlaylistInstance:
    """
    PlaylistInstance class represents an instance of a playlist asset.
    """

    # pylint: disable-msg=too-many-arguments
    def __init__(self, name: str, playlist: dict, track_crossfade_time: float,
                 context: Optional[str] = None, settings: Optional[dict] = None):
        """Constructor"""
        self._name = name
        if playlist is None:
            raise ValueError("Cannot create playlist instance: playlist parameter is None")

        self._context = context

        if settings is None:
            settings = {}

        # Set crossfade time that will be used for playing this instance (will either
        # use the track time or the playlist time depending upon the crossfade_mode
        # setting
        settings.setdefault('crossfade_mode', playlist['crossfade_mode'])
        if settings['crossfade_mode'] == 'use_track_setting':
            settings['crossfade_time'] = track_crossfade_time
        elif settings['crossfade_mode'] == 'use_playlist_setting':
            if playlist['crossfade_mode'] == 'use_track_setting':
                settings['crossfade_time'] = track_crossfade_time
            else:
                settings.setdefault('crossfade_time', playlist['crossfade_time'])
        else:
            settings.setdefault('crossfade_time', playlist['crossfade_time'])

        settings.setdefault('shuffle', playlist['shuffle'])
        settings.setdefault('repeat', playlist['repeat'])
        settings['sounds'] = playlist['sounds']
        settings.setdefault('events_when_played', playlist['events_when_played'])
        settings.setdefault('events_when_stopped', playlist['events_when_stopped'])
        settings.setdefault('events_when_looping', playlist['events_when_looping'])
        settings.setdefault('events_when_sound_changed', playlist['events_when_sound_changed'])
        settings.setdefault('events_when_sound_stopped', playlist['events_when_sound_stopped'])
        self._settings = settings

        self._sounds = Randomizer(self._settings['sounds'])
        self._sounds.disable_random = not self._settings['shuffle']
        self._sounds.force_all = True
        self._sounds.force_different = True
        self._sounds.loop = self._settings['repeat']

        self._current_sound_instance = None
        self._fading_sound_instance = None

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<PlaylistInstance: {}>'.format(self.name)

    @property
    def name(self):
        return self._name

    @property
    def crossfade_time(self):
        return self._settings['crossfade_time']

    @property
    def shuffle(self):
        return self._settings['shuffle']

    @property
    def repeat(self):
        return self._settings['repeat']

    @property
    def events_when_played(self):
        return self._settings['events_when_played']

    @property
    def events_when_stopped(self):
        return self._settings['events_when_stopped']

    @property
    def events_when_looping(self):
        return self._settings['events_when_looping']

    @property
    def events_when_sound_changed(self):
        return self._settings['events_when_sound_changed']

    @property
    def events_when_sound_stopped(self):
        return self._settings['events_when_sound_stopped']

    @property
    def sounds(self):
        return self._settings['sounds']

    @property
    def end_of_playlist(self):
        if self._sounds.disable_random:
            return self._sounds.data['current_item_index'] == len(self._sounds.items)
        else:
            return len(self._sounds.data['items_sent']) == len(self._sounds.items)

    @property
    def current_sound_instance(self):
        """Return the current sound instance"""
        return self._current_sound_instance

    @current_sound_instance.setter
    def current_sound_instance(self, value):
        """Set the current sound instance"""
        self._current_sound_instance = value

    @property
    def fading_sound_instance(self):
        """Return the fading sound instance"""
        return self._fading_sound_instance

    @fading_sound_instance.setter
    def fading_sound_instance(self, value):
        """Set the fading sound instance"""
        self._fading_sound_instance = value

    @property
    def context(self):
        """The context under which this playlist was created/played."""
        return self._context

    def get_next_sound_name(self):
        """Return the name of the next sound in the playlist (advance iterator)"""
        try:
            return self._sounds.get_next()
        except StopIteration:
            return None

    def get_current_sound_name(self):
        """Return the name of the current sound in the playlist"""
        try:
            return self._sounds.get_current()
        except StopIteration:
            return None


CollectionCls = PlaylistCollection
