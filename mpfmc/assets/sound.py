"""Contains sound-related asset classes used by the audio system"""

import logging

from mpf.core.assets import Asset, AssetPool
from mpf.core.utility_functions import Util
from mpfmc.core.audio.audio_interface import AudioInterface, AudioException


# ---------------------------------------------------------------------------
#    Default sound asset configuration parameter values
# ---------------------------------------------------------------------------
DEFAULT_VOLUME = 0.5
DEFAULT_PRIORITY = 0
DEFAULT_MAX_QUEUE_TIME = None
DEFAULT_LOOPS = 0
MINIMUM_DUCKING_DURATION = "10ms"


class SoundPool(AssetPool):
    """Allows several Sound assets to be grouped together in a 'pool' and referenced
    as a single sound when playing back.  Allows for easily managed variations
    of a sound.
    """
    # Be sure the pool group, if you use it, is first in the file ahead of the
    # asset class.

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<SoundPool: {}>'.format(self.name)

    @property
    def sound(self):
        """The currently selected Sound object from the pool"""
        return self.asset

    def play(self, settings=None):
        """
        Plays the sound using the specified settings
        Args:
            settings: Optional dictionary of settings to override the default values.
        """
        self.sound.play(settings)

    def stop(self):
        """
        Stops all instances of all sounds contained in the sound pool.
        """
        for sound in self.assets:
            # Assets contain a list of tuples (sound, number)
            sound[0].stop()

    def stop_looping(self):
        """Stops looping on all instances of all sounds contained in the sound pool."""
        for sound in self.assets:
            # Assets contain a list of tuples (sound, number)
            sound[0].stop_looping()


class SoundAsset(Asset):
    """
    Sound asset class contains a single sound that may be played using the audio engine.

    Notes:
        It is critical that the AudioInterface be initialized before any Sound assets
        are loaded.  The loading code relies upon having an active audio interface.
    """
    attribute = 'sounds'  # attribute in MC, e.g. self.mc.images
    path_string = 'sounds'  # entry from mpf_mc:paths: for asset folder name
    config_section = 'sounds'  # section in the config files for this asset
    extensions = ('wav',)  # Additional extensions may be added at runtime ('ogg',
    # 'flac') depending upon the SDL_Mixer plug-ins installed on the system
    class_priority = 100  # Order asset classes will be loaded. Higher is first.
    pool_config_section = 'sound_pools'  # Will setup groups if present
    asset_group_class = SoundPool  # Class or None to not use pools

    def __init__(self, mc, name, file, config):
        """ Constructor"""
        super().__init__(mc, name, file, config)

        self._track = None
        self._volume = DEFAULT_VOLUME
        self.priority = DEFAULT_PRIORITY
        self._max_queue_time = DEFAULT_MAX_QUEUE_TIME
        self._loops = DEFAULT_LOOPS
        self._events_when_played = None
        self._events_when_stopped = None
        self._events_when_looping = None
        self._container = None  # holds the actual sound samples in memory
        self._ducking = None
        self.log = logging.getLogger('SoundAsset')

        # Make sure a legal track name has been specified (unless only one track exists)
        if 'track' not in self.config:
            # Track not specified, determine track count
            if self.machine.sound_system.audio_interface.get_track_count() == 1:
                # Only one track exists, assign default track
                track = self.machine.sound_system.audio_interface.get_track(0)
            else:
                # More than one track exists, raise error
                self.log.error("sound must have a valid track name. "
                               "Could not create sound '%s' asset.", name)
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
                                     "Could not create sound '{}' asset".format(self.config['track'], name))

        self._track = track

        # Validate sound attributes and provide default values
        if 'volume' in self.config:
            self._volume = min(max(float(self.config['volume']), 0.0), 1.0)

        if 'priority' in self.config:
            self.priority = int(self.config['priority'])

        if 'max_queue_time' in self.config and self.config['max_queue_time'] is not None:
            self._max_queue_time = AudioInterface.string_to_secs(self.config['max_queue_time'])

        if 'loops' in self.config:
            self._loops = int(self.config['loops'])

        if 'events_when_played' in self.config and isinstance(
                self.config['events_when_played'], str):
            self._events_when_played = Util.string_to_list(self.config['events_when_played'])

        if 'events_when_stopped' in self.config and isinstance(
                self.config['events_when_stopped'], str):
            self._events_when_stopped = Util.string_to_list(self.config['events_when_stopped'])

        if 'events_when_looping' in self.config and isinstance(
                self.config['events_when_looping'], str):
            self._events_when_looping = Util.string_to_list(self.config['events_when_looping'])

        if 'ducking' in self.config:
            self._ducking = DuckingSettings(self.machine, self.config['ducking'])

            # An attenuation value of exactly 1.0 does absolutely nothing so
            # there is no point in keeping the ducking settings for this
            # sound when attenuation is 1.0.
            if self._ducking.attenuation == 1.0:
                self._ducking = None

        # Add sound to a dictionary of sound objects keyed by sound id
        if not hasattr(self.machine, 'sounds_by_id'):
            setattr(self.machine, 'sounds_by_id', dict())

        self.machine.sounds_by_id[self.id] = self

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<Sound: {}({}), Loaded={}>'.format(self.name, self.id, self.loaded)

    def __lt__(self, other):
        """Less than comparison operator"""
        # Note this is "backwards" (It's the __lt__ method but the formula uses
        # greater than because the PriorityQueue puts lowest first.)
        if other is None:
            return False
        else:
            return ("%s, %s" % (self.priority, self._id) >
                    "%s, %s" % (other.priority, other.get_id()))

    @property
    def id(self):
        """
        The id property contains a unique identifier for the sound (based on the Python id()
        function).  This id is used in the audio interface to uniquely identify a sound
        (rather than the name) due to the hassle of passing strings between Python and Cython.
        Returns:
            An integer uniquely identifying the sound
        """
        return id(self)

    @property
    def track(self):
        """The track object on which to play the sound"""
        return self._track

    @property
    def volume(self):
        """Returns the volume of the sound (float 0.0 to 1.0)"""
        return self._volume

    @property
    def max_queue_time(self):
        """Returns the maximum time a sound may be queued before
        playing or being discarded"""
        return self._max_queue_time

    @property
    def loops(self):
        """Returns the looping setting for the sound.
        0 - do not loop, -1 loop infinitely, >= 1 the number of
        times to loop."""
        return self._loops

    @property
    def events_when_played(self):
        """Returns the list of events that are posted when the sound is played"""
        return self._events_when_played

    @property
    def events_when_stopped(self):
        """Returns the list of events that are posted when the sound is stopped"""
        return self._events_when_stopped

    @property
    def events_when_looping(self):
        """Returns the list of events that are posted when the sound begins a new loop"""
        return self._events_when_looping

    @property
    def container(self):
        """The container object wrapping the SDL structure containing the actual sound data"""
        return self._container

    @property
    def ducking(self):
        """A DuckingSettings object containing the ducking settings for this sound (optional)"""
        return self._ducking

    @property
    def has_ducking(self):
        """Returns whether or not this sound has ducking"""
        return self._ducking is not None

    def do_load(self):
        """Loads the sound asset from disk."""

        # Load the sound file into memory
        try:
            self._container = AudioInterface.load_sound(self.file)
        except AudioException as exception:
            self.log.error("Load sound %s failed due to an exception - %s",
                           self.name, str(exception))
            raise

        # Validate ducking now that the sound has been loaded
        if self._ducking is not None:
            try:
                self._ducking.validate(self._container.length)
            except AudioException as exception:
                self.log.error("Ducking settings for sound %s are not valid: %s",
                               self.name, str(exception))
                raise

    def _do_unload(self):
        """Unloads the asset from memory"""

        AudioInterface.unload_sound(self._container)
        self._container = None

    def is_loaded(self):
        """Called when the asset has finished loading"""
        super().is_loaded()
        self.log.debug("Loaded %s (Track %s)", self.name, self.track)

    def play(self, settings=None):
        """
        Plays the sound using the specified settings
        Args:
            settings: Optional dictionary of settings to override the default values.
        """
        self.log.debug("Play sound %s %s", self.name, self.track)
        self._track.play_sound(self, **settings)

    def stop(self):
        """Stops all instances of the sound playing on the sound's default track."""
        self.log.debug("Stop sound %s %s", self.name, self.track)
        self._track.stop_sound(self)

    def stop_looping(self):
        """Stops looping on all instances of the sound playing (and awaiting playback)."""
        self.log.debug("Stop looping sound %s %s", self.name, self.track)
        self._track.stop_sound_looping(self)


class DuckingSettings(object):
    """ DuckingSettings contains the parameters needed to control audio ducking
    for a sound.
    """

    def __init__(self, mc, config):
        """
        Constructor
        Args:
            mc: The media controller instance.
            config: The ducking configuration file section that contains all the ducking
                settings for the sound.

        Notes:
            The config section should contain the following attributes:
                target: The track name to apply the ducking to when the sound is played.
                delay: The duration (in samples) of the delay period (time before attack starts)
                attack: The duration (in samples) of the attack stage of the ducking envelope
                attenuation: The attenuation (gain) (0.0 to 1.0) to apply to the target track while
                    ducking
                release_point: The point (in samples) relative to the end of the sound at which
                    to start the release stage.  A positive value indicates prior to the end of
                    the sound while a negative value indicates to start the release after the
                    end of the sound.
                release: The duration (in samples) of the release stage of the ducking process.
        """
        if config is None:
            raise AudioException("The 'ducking' configuration must include the following "
                                 "attributes: track, delay, attack, attenuation, "
                                 "release_point, and release")

        if 'target' not in config:
            raise AudioException("'ducking.target' must contain at least one "
                                 "valid audio track name")

        self._track = mc.sound_system.audio_interface.get_track_by_name(config['target'])
        if self._track is None:
            raise AudioException("'ducking.target' must contain a valid audio track name")

        # Delay is optional (defaults to 0, must be >= 0)
        if 'delay' in config:
            self._delay = max(mc.sound_system.audio_interface.string_to_samples(
                config['delay']), 0)
        else:
            self._delay = 0

        if 'attack' not in config:
            raise AudioException("'ducking.attack' must contain a valid attack value (time "
                                 "string or number of samples)")
        self._attack = max(mc.sound_system.audio_interface.string_to_samples(config['attack']),
                           mc.sound_system.audio_interface.string_to_samples(
                               MINIMUM_DUCKING_DURATION))

        if 'attenuation' not in config:
            raise AudioException("'ducking.attenuation' must contain valid attenuation "
                                 "value (0.0 to 1.0)")
        self._attenuation = min(max(float(AudioInterface.string_to_gain(
            config['attenuation'])), 0.0), 1.0)

        if 'release_point' not in config:
            raise AudioException("'ducking.release_point' must contain a valid release point "
                                 "value (time string or number of samples)")
        # Release point cannot be negative (must be before or at the end of the sound)
        self._release_point = max(mc.sound_system.audio_interface.string_to_samples(
            config['release_point']), 0)

        if 'release' not in config:
            raise AudioException("'ducking.release' must contain a valid release "
                                 "value (time string or number of samples)")
        self._release = max(mc.sound_system.audio_interface.string_to_samples(config['release']),
                            mc.sound_system.audio_interface.string_to_samples(
                                MINIMUM_DUCKING_DURATION))

    @property
    def track(self):
        """ The track object to apply the ducking envelope"""
        return self._track

    @property
    def delay(self):
        """The duration (in samples) of the delay period (time before attack starts)"""
        return self._delay

    @property
    def attack(self):
        """The duration (in samples) of the attack stage of the ducking envelope"""
        return self._attack

    @property
    def attenuation(self):
        """The attenuation (gain) (0.0 to 1.0) to apply to the target track while ducking"""
        return self._attenuation

    @property
    def release_point(self):
        """The point (in samples) relative to the end of the sound at which
        to start the release stage.  A positive value indicates prior to the end of
        the sound while a negative value indicates to start the release after the
        end of the sound.
        """
        return self._release_point

    @property
    def release(self):
        """The duration (in samples) of the release stage of the ducking process."""
        return self._release

    def validate(self, sound_length):
        """
        Validates the ducking settings against the length of the sound to ensure all
        settings are valid.
        Args:
            sound_length: The length of the sound in samples

        Returns:
            True if all settings are valid, otherwise an exception will be thrown
        """
        if sound_length is None or sound_length == 0:
            raise AudioException("ducking may not be applied to an empty/zero length sound")

        if self._attack > sound_length:
            raise AudioException("'ducking.attack' value may not be longer than the "
                                 "length of the sound")

        if self._release_point >= sound_length:
            raise AudioException("'ducking.release_point' value may not occur before the "
                                 "beginning of the sound")

        if self._release_point + self._attack >= sound_length:
            raise AudioException("'ducking.release_point' value may not occur before "
                                 "the ducking attack segment has completed")

        return True
