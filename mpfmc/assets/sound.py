"""Contains sound-related asset classes used by the audio system"""

import logging
from enum import Enum, unique

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
        Play the sound using the specified settings
        Args:
            settings: Optional dictionary of settings to override the default values.
        """
        self.sound.play(settings)

    def stop(self):
        """
        Stop all instances of all sounds contained in the sound pool.
        """
        for sound in self.assets:
            # Assets contain a list of tuples (sound, number)
            sound[0].stop()

    def stop_looping(self):
        """Stop looping on all instances of all sounds contained in the sound pool."""
        for sound in self.assets:
            # Assets contain a list of tuples (sound, number)
            sound[0].stop_looping()


# pylint: disable=too-many-instance-attributes
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

    # pylint: disable=too-many-branches, too-many-statements
    def __init__(self, mc, name, file, config):
        """ Constructor"""
        super().__init__(mc, name, file, config)

        self._track = None
        self._volume = DEFAULT_VOLUME
        self.priority = DEFAULT_PRIORITY
        self._max_queue_time = DEFAULT_MAX_QUEUE_TIME
        self._loops = DEFAULT_LOOPS
        self._fade_in = 0
        self._events_when_played = None
        self._events_when_stopped = None
        self._events_when_looping = None
        self._markers = list()
        self._container = None  # holds the actual sound samples in memory
        self._ducking = None
        self._instances = list()
        self.log = logging.getLogger('SoundAsset')

        # Make sure a legal track name has been specified.  If not, throw an exception
        track = self.machine.sound_system.audio_interface.get_track_by_name(self.config['track'])
        if 'track' not in self.config or track is None:
            self.log.error("Sound must have a valid track name. "
                           "Could not create sound '%s' asset.", name)
            raise AudioException("Sound must have a valid track name. "
                                 "Could not create sound '{}' asset".format(name))

        self._track = track

        # Validate sound attributes and provide default values
        if 'volume' in self.config:
            self._volume = float(self.config['volume'])
            if self._volume < 0.0 or self._volume > 1.0:
                raise AudioException("volume must be a value between 0.0 and 1.0 in sound %s",
                                     self.name)

        if 'priority' in self.config:
            self.priority = int(self.config['priority'])

        if 'max_queue_time' in self.config and self.config['max_queue_time'] is not None:
            self._max_queue_time = AudioInterface.string_to_secs(self.config['max_queue_time'])
            if self._max_queue_time < 0:
                raise AudioException("max_queue_time must be a positive value in sound %s",
                                     self.name)

        if 'loops' in self.config:
            self._loops = int(self.config['loops'])

        if 'fade_in' in self.config:
            self._fade_in = AudioInterface.string_to_secs(self.config['fade_in'])
            if self._fade_in < 0:
                raise AudioException("fade_in must be a positive value in sound %s", self.name)

        if 'events_when_played' in self.config and isinstance(
                self.config['events_when_played'], str):
            self._events_when_played = Util.string_to_list(self.config['events_when_played'])

        if 'events_when_stopped' in self.config and isinstance(
                self.config['events_when_stopped'], str):
            self._events_when_stopped = Util.string_to_list(self.config['events_when_stopped'])

        if 'events_when_looping' in self.config and isinstance(
                self.config['events_when_looping'], str):
            self._events_when_looping = Util.string_to_list(self.config['events_when_looping'])

        if 'markers' in self.config:
            self._markers = SoundAsset.load_markers(self.config['markers'], self.name)

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

    #pylint: disable=invalid-name
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
        """Return the volume of the sound (float 0.0 to 1.0)"""
        return self._volume

    @property
    def max_queue_time(self):
        """Return the maximum time a sound may be queued before
        playing or being discarded"""
        return self._max_queue_time

    @property
    def loops(self):
        """Return the looping setting for the sound.
        0 - do not loop, -1 loop infinitely, >= 1 the number of
        times to loop."""
        return self._loops

    @property
    def fade_in(self):
        """Return the fade in time for the sound (in seconds)"""
        return self._fade_in

    @property
    def events_when_played(self):
        """Return the list of events that are posted when the sound is played"""
        return self._events_when_played

    @property
    def events_when_stopped(self):
        """Return the list of events that are posted when the sound is stopped"""
        return self._events_when_stopped

    @property
    def events_when_looping(self):
        """Return the list of events that are posted when the sound begins a new loop"""
        return self._events_when_looping

    @property
    def container(self):
        """The container object wrapping the SDL structure containing the actual sound data"""
        return self._container

    @property
    def markers(self):
        """List of marker dictionary objects containing markers for this sound (optional)"""
        return self._markers

    @property
    def ducking(self):
        """A DuckingSettings object containing the ducking settings for this sound (optional)"""
        return self._ducking

    @property
    def has_ducking(self):
        """Return whether or not this sound has ducking"""
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

        # Stop all sound instances immediately
        self.stop()

        # Unload the sound (uses lock to ensure it is not currently playing)
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
        sound_instance = SoundInstance(self, settings)
        if sound_instance is not None:
            self._instances.append(sound_instance)
            self._track.play_sound(sound_instance)

        return sound_instance

    def stop(self):
        """Stop all instances of the sound playing on the sound's default track."""
        self.log.debug("Stop sound %s %s", self.name, self.track)

        for sound_instance in self._instances:
            if not sound_instance.finished:
                sound_instance.stop()

        self._instances.clear()
        self._track.stop_sound(self)

    def stop_looping(self):
        """Stop looping on all instances of the sound playing (and awaiting playback)."""
        self.log.debug("Stop looping sound %s %s", self.name, self.track)
        self._track.stop_sound_looping(self)

    @staticmethod
    def load_markers(config, sound_name):
        """
        Load and validate the markers config section
        Args:
            config: The 'markers' configuration file section for the sound
            sound_name: The name of the sound

        Returns:
            List of sound marker dictionary objects
        """

        markers = list()

        if isinstance(config, dict):
            config_markers = list(config)
        elif isinstance(config, list):
            config_markers = config
        else:
            raise AudioException("Sound %s has an invalid markers section", sound_name)

        last_marker_time = 0

        # Loop over all markers in the list
        for settings in config_markers:
            marker = dict()

            # Set marker parameters
            marker['time'] = AudioInterface.string_to_secs(settings['time'])
            if marker['time'] < last_marker_time:
                raise AudioException("Sound markers for sound %s must be in ascending time order",
                                     sound_name)
            last_marker_time = marker['time']

            if 'events' in settings and settings['events'] is not None:
                marker['events'] = Util.string_to_list(settings['events'])
            else:
                raise AudioException("Sound markers for sound %s must specify at least one event",
                                     sound_name)

            if 'name' in settings and settings['name'] is not None:
                marker['name'] = settings['name'].lower()
            else:
                marker['name'] = None

            markers.append(marker)

        return markers


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
        Validate the ducking settings against the length of the sound to ensure all
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


@unique
class SoundInstanceStatus(Enum):
    """Enumerated class containing status values for SoundInstance class."""
    pending = 0
    queued = 1
    playing = 2
    finished = 3


# pylint: disable=too-many-public-methods
class SoundInstance(object):
    """An instance of a playing sound asset. This class is essentially a wrapper container
    for sound assets that contains all the overridden parameter values for playback."""

    # pylint: disable=too-many-branches
    def __init__(self, sound, settings=None):
        """
        Constructor
        Args:
            sound: The sound to create an instance of
            settings: Settings dictionary of sound parameters to override in this instance
        """
        if sound is None:
            raise ValueError("Cannot create sound instance: sound parameter is None")

        # pylint: disable=invalid-name
        self.mc = sound.machine
        self._time = self.mc.clock.get_time()
        self._sound = sound
        self._status = SoundInstanceStatus.pending
        self._played = False
        self._track = sound.track
        self._loop_count = 0
        self._fade_in = 0.0
        self._markers = list()
        self.log = logging.getLogger('SoundInstance')

        # Validate settings that can be overridden
        if 'priority' in settings and settings['priority'] is not None:
            self._priority = settings['priority']
        else:
            self._priority = sound.priority

        if 'loops' in settings and settings['loops'] is not None:
            self._loops = settings['loops']
        else:
            self._loops = sound.loops

        if 'max_queue_time' in settings:
            self._max_queue_time = settings['max_queue_time']
        else:
            self._max_queue_time = sound.max_queue_time

        if 'volume' in settings and settings['volume'] is not None:
            self._volume = settings['volume']
        else:
            self._volume = sound.volume

        if 'fade_in' in settings:
            self._fade_in = AudioInterface.string_to_secs(settings['fade_in'])
            if self._fade_in < 0.0:
                raise AudioException("fade_in must be a positive value in sound %s", self.name)

        if 'events_when_played' in settings:
            self._events_when_played = settings['events_when_played']
        else:
            self._events_when_played = sound.events_when_played

        if 'events_when_stopped' in settings:
            self._events_when_stopped = settings['events_when_stopped']
        else:
            self._events_when_stopped = sound.events_when_stopped

        if 'events_when_looping' in settings:
            self._events_when_looping = settings['events_when_looping']
        else:
            self._events_when_looping = sound.events_when_looping

        if 'markers' in settings:
            self._markers = SoundAsset.load_markers(settings['markers'], self.name)
        else:
            self._markers = sound.markers

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<SoundInstance: {}({}), Loaded={}>'.format(
            self.sound.name, self.id, self.sound.loaded)

    def __lt__(self, other):
        """Less than comparison operator"""
        # Note this is "backwards" (It's the __lt__ method but the formula uses
        # greater than because the PriorityQueue puts lowest first.)
        if other is None:
            return False
        else:
            return ("%s, %s, %s" % (self.priority, self.sound.get_id(), self.id) >
                    "%s, %s, %s" % (other.priority, other.sound.get_id(), other.id))

    # pylint: disable=invalid-name
    @property
    def id(self):
        """
        The id property contains a unique identifier for the sound reference(based on the Python
        id() function).  This id is used in the audio interface to uniquely identify a sound
        instance (rather than the name) due to the hassle of passing strings between Python and
        Cython.
        Returns:
            An integer uniquely identifying the sound reference
        """
        return id(self)

    @property
    def sound(self):
        """The sound asset wrapped by this object"""
        return self._sound

    @property
    def loaded(self):
        """Return whether or not the underlying sound asset file is loaded into memory"""
        return self._sound.loaded

    @property
    def name(self):
        """The name of the sound"""
        return self.sound.name

    @property
    def track(self):
        """The track object on which to play the sound"""
        return self._track

    @property
    def volume(self):
        """Return the volume of the sound (float 0.0 to 1.0)"""
        return self._volume

    @property
    def priority(self):
        """Return the priority of the sound"""
        return self._priority

    @property
    def max_queue_time(self):
        """Return the maximum time a sound may be queued before
        playing or being discarded"""
        return self._max_queue_time

    @property
    def loops(self):
        """Return the looping setting for the sound.
        0 - do not loop, -1 loop infinitely, >= 1 the number of
        times to loop."""
        return self._loops

    @property
    def fade_in(self):
        """Return the fade in time for the sound (in seconds)"""
        return self._fade_in

    @property
    def events_when_played(self):
        """Return the list of events that are posted when the sound is played"""
        return self._events_when_played

    @property
    def events_when_stopped(self):
        """Return the list of events that are posted when the sound is stopped"""
        return self._events_when_stopped

    @property
    def events_when_looping(self):
        """Return the list of events that are posted when the sound begins a new loop"""
        return self._events_when_looping

    @property
    def markers(self):
        """Return the list of marker dictionary objects for the sound"""
        return self._markers

    @property
    def container(self):
        """The container object wrapping the SDL structure containing the actual sound data"""
        return self.sound.container

    @property
    def ducking(self):
        """A DuckingSettings object containing the ducking settings for this sound (optional)"""
        return self.sound.ducking

    @property
    def has_ducking(self):
        """Return whether or not this sound has ducking"""
        return self.sound.ducking is not None

    @property
    def queued(self):
        """Indicates whether or not this sound reference is currently queued for playback."""
        return self._status == SoundInstanceStatus.queued

    @property
    def pending(self):
        """Indicates whether or not this sound instance is currently pending playback."""
        return self._status == SoundInstanceStatus.pending or \
            self._status == SoundInstanceStatus.queued

    @property
    def playing(self):
        """Return whether or not this sound instance is currently playing."""
        return self._status == SoundInstanceStatus.playing

    def notify_pending(self):
        """Set the sound instance status to pending."""
        self._status = SoundInstanceStatus.pending

    def notify_queued(self):
        """Notifies the sound instance that it is now queued and triggers any
        corresponding actions"""
        self._status = SoundInstanceStatus.queued

    def notify_playing(self):
        """Notifies the sound instance that it is now playing and triggers any
        corresponding actions."""
        self._status = SoundInstanceStatus.playing
        self._played = True
        if self.events_when_played is not None:
            for event in self.events_when_played:
                self.mc.bcp_processor.send('trigger', name=event)

    def notify_stopped(self):
        """Notifies the sound instance that it has now stopped and triggers any
        corresponding actions."""

        # Trigger any events
        if self.events_when_stopped is not None:
            for event in self.events_when_stopped:
                self.mc.bcp_processor.send('trigger', name=event)

        self._finished()

    def notify_looping(self):
        """Notifies the sound instance that it is now looping and triggers any
        corresponding actions."""
        # Increment the total loop count (how many times has instance looped)
        self._loop_count += 1

        # Trigger any events
        if self.events_when_looping is not None:
            for event in self.events_when_looping:
                self.mc.bcp_processor.send('trigger', name=event)

    def notify_marker(self, number):
        """
        Notify the sound instance that the specified marker has been reached
        during playback and trigger any corresponding actions.
        Args:
            number: The marker number
        """
        if len(self.markers) == 0 or number not in range(len(self.markers)):
            raise AudioException('Unknown marker triggered in sound instance %s (%s)',
                                 self.name, self.id)

        if 'events' in self.markers[number] and self.markers[number]['events'] is not None:
            for event in self.markers[number]['events']:
                self.mc.bcp_processor.send('trigger', name=event)

    def notify_expired(self):
        """Notifies the sound instance that it has expired and will not be played."""
        self._finished()

    def notify_canceled(self):
        """Notifies the sound instance that is has been canceled and will not be played."""
        self._finished()

    def _finished(self):
        """Internal function to trigger finished state and related processing."""
        self._status = SoundInstanceStatus.finished

        # TODO: call any finished callback functions

        # Remove the instance from the list of active instances for the parent sound
        del self.sound.instances[self.id]

    @property
    def status(self):
        """Return the current status of the sound instance."""
        return self._status

    @property
    def played(self):
        """Return whether or not this sound instance has been played."""
        return self._played

    @property
    def finished(self):
        """Return whether or not this sound instance has finished playing."""
        return self._status == SoundInstanceStatus.finished

    @property
    def loop_count(self):
        """Return how many times this sound instance has looped back to the beginning."""
        return self._loop_count

    def stop(self):
        """Stops the sound instance."""
        self._track.stop_sound(self)

    def stop_looping(self):
        """Stops looping the sound instance."""
        self._track.stop_sound_looping(self)
