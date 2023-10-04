"""Audio module provides all the audio features (playing of sounds) for the media controller."""
import logging

from kivy.clock import Clock
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.utility_functions import Util
from mpfmc.core.audio.audio_interface import AudioInterface
from mpfmc.core.audio.audio_exception import AudioException

__all__ = ('SoundSystem',
           'AudioInterface',
           'AudioException')

# ---------------------------------------------------------------------------
#    Default sound system and track values
# ---------------------------------------------------------------------------
DEFAULT_AUDIO_ENABLED = True
DEFAULT_AUDIO_BUFFER_SAMPLE_SIZE = 2048
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_AUDIO_CHANNELS = 1
DEFAULT_MASTER_VOLUME = 0.5
DEFAULT_TRACK_MAX_SIMULTANEOUS_SOUNDS = 1
DEFAULT_TRACK_VOLUME = 0.5


# pylint: disable=too-many-instance-attributes
class SoundSystem:

    """Sound system for MPF.

    The SoundSystem class is used to read the sound system settings from the
    config file and then initialize the audio interface and create the
    specified tracks.
    """

    # pylint: disable=invalid-name, too-many-branches
    def __init__(self, mc):
        """initialize sound system."""
        self.mc = mc
        self.log = logging.getLogger('SoundSystem')
        self._initialized = False
        self.audio_interface = None
        self.config = dict()
        self.sound_events = dict()
        self.tracks = CaseInsensitiveDict()
        self.clock_event = None

        self.log.debug("Loading the Sound System")

        # Load configuration for sound system
        if 'sound_system' not in self.mc.machine_config:
            self.log.info("SoundSystem: Using default 'sound_system' settings")
            self.config = dict()
        else:
            self.config = self.mc.machine_config['sound_system']

        # TODO: Use config spec validator

        # Validate configuration and provide default values where needed
        if 'enabled' not in self.config:
            self.config['enabled'] = DEFAULT_AUDIO_ENABLED

        # If the sound system has been disabled, abort initialization
        if not self.config['enabled']:
            self.log.info("SoundSystem: The sound system has been disabled in "
                          "the configuration file (enabled: False). No audio "
                          "features will be available.")
            return

        if 'buffer' not in self.config or self.config['buffer'] == 'auto':
            self.config['buffer'] = DEFAULT_AUDIO_BUFFER_SAMPLE_SIZE
        elif not AudioInterface.power_of_two(self.config['buffer']):
            self.log.warning("SoundSystem: The buffer setting is not a power of "
                             "two. Default buffer size will be used.")
            self.config['buffer'] = DEFAULT_AUDIO_BUFFER_SAMPLE_SIZE

        if 'frequency' not in self.config or self.config['frequency'] == 'auto':
            self.config['frequency'] = DEFAULT_SAMPLE_RATE

        if 'channels' not in self.config:
            self.config['channels'] = DEFAULT_AUDIO_CHANNELS

        # Initialize audio interface library (get audio output)
        try:
            self.audio_interface = AudioInterface(
                rate=self.config['frequency'],
                channels=self.config['channels'],
                buffer_samples=self.config['buffer'])
        except AudioException:
            self.log.error("Could not initialize the audio interface. "
                           "Audio features will not be available.")
            self.audio_interface = None
            return

        # Setup tracks in audio system (including initial volume levels)
        if 'tracks' in self.config:
            for track_name, track_config in self.config['tracks'].items():
                self._create_track(track_name, track_config)
        else:
            self._create_track('default')
            self.log.info("No audio tracks are specified in your machine config file. "
                          "a track named 'default' has been created.")

        # Set initial master volume level to off
        self.master_volume = 0.0
        if "master_volume" in self.config:
            raise ValueError("master_volume in sound_system is deprecated. Use the 'master_volume' machine_var instead.")

        # Establish machine tick function callback (will process internal audio events)
        self.clock_event = Clock.schedule_interval(self.tick, 0)

        # Start audio engine processing
        self.audio_interface.enable()
        self._initialized = True

        self.mc.events.add_handler("shutdown", self.shutdown)
        self.mc.events.add_handler("machine_var_master_volume", self._set_volume)

    def _set_volume(self, **kwargs):
        self.master_volume = kwargs['value']

    def shutdown(self, **kwargs):
        """Shuts down the audio interface"""
        del kwargs
        if self.enabled:
            self.audio_interface.shutdown()
            self._initialized = False

    @property
    def enabled(self):
        """Return true if enabled."""
        return self._initialized

    @property
    def master_volume(self) -> float:
        """Return master volume."""
        return self.audio_interface.get_master_volume()

    @master_volume.setter
    def master_volume(self, value: float):
        """Set master volume."""
        # Constrain volume to the range 0.0 to 1.0
        value = min(max(value, 0.0), 1.0)
        self.audio_interface.set_master_volume(value)
        self.log.info("Setting master volume to %s", value)

    @property
    def default_track(self):
        """Return default track."""
        return self.audio_interface.get_track(0)

    def _create_track(self, name, config=None):     # noqa
        """Create a track in the audio system with the specified name and configuration.

        Args:
            name: The track name (which will be used to reference the track, such as
                "voice" or "sfx".
            config: A Python dictionary containing the configuration settings for
                this track.
        """
        if self.audio_interface is None:
            raise AudioException("Could not create '{}' track - the sound_system has "
                                 "not been initialized".format(name))

        # Validate track config parameters
        if name in self.tracks:
            raise AudioException("Could not create '{}' track - a track with that name "
                                 "already exists".format(name))

        if not config:
            config = {}

        if 'volume' not in config:
            config['volume'] = DEFAULT_TRACK_VOLUME

        if 'type' not in config:
            config['type'] = 'standard'

        if config['type'] not in ['standard', 'playlist', 'sound_loop']:
            raise AudioException("Could not create '{}' track - an illegal value for "
                                 "'type' was found".format(name))

        # Validate type-specific parameters and create the track
        track = None
        if config['type'] == 'standard':
            if 'simultaneous_sounds' not in config:
                config['simultaneous_sounds'] = DEFAULT_TRACK_MAX_SIMULTANEOUS_SOUNDS

            track = self.audio_interface.create_standard_track(self.mc,
                                                               name,
                                                               config['simultaneous_sounds'],
                                                               config['volume'])
        elif config['type'] == 'playlist':
            config.setdefault('crossfade_time', 0.0)
            config['crossfade_time'] = Util.string_to_secs(config['crossfade_time'])

            track = self.audio_interface.create_playlist_track(self.mc,
                                                               name,
                                                               config['crossfade_time'],
                                                               config['volume'])

        elif config['type'] == 'sound_loop':
            if 'max_layers' not in config:
                config['max_layers'] = 8

            track = self.audio_interface.create_sound_loop_track(self.mc,
                                                                 name,
                                                                 config['max_layers'],
                                                                 config['volume'])

        if track is None:
            raise AudioException("Could not create '{}' track due to an error".format(name))

        self.tracks[name] = track

        if 'events_when_stopped' in config and config['events_when_stopped'] is not None:
            track.events_when_stopped = Util.string_to_event_list(config['events_when_stopped'])

        if 'events_when_played' in config and config['events_when_played'] is not None:
            track.events_when_played = Util.string_to_event_list(config['events_when_played'])

        if 'events_when_paused' in config and config['events_when_paused'] is not None:
            track.events_when_paused = Util.string_to_event_list(config['events_when_paused'])

        if 'events_when_resumed' in config and config['events_when_resumed'] is not None:
            track.events_when_resumed = Util.string_to_event_list(config['events_when_resumed'])

    def tick(self, dt):
        """Clock callback function"""
        del dt
        self.audio_interface.process()
