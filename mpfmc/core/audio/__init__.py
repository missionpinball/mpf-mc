"""Audio module provides all the audio features (playing of sounds) for the media controller."""
import logging

from kivy.clock import Clock
from mpfmc.core.audio.audio_interface import AudioInterface, AudioException, Track
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.utility_functions import Util

__all__ = ('SoundSystem',
           'AudioInterface',
           'AudioException',
           'Track',
          )

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
class SoundSystem(object):

    """Sound system for MPF.

    The SoundSystem class is used to read the sound system settings from the
    config file and then initialize the audio interface and create the
    specified tracks.
    """

    # pylint: disable=invalid-name, too-many-branches
    def __init__(self, mc):
        """Initialise sound system."""
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

        # Validate configuration and provide default values where needed
        if 'enabled' not in self.config:
            self.config['enabled'] = DEFAULT_AUDIO_ENABLED

        # If the sound system has been disabled, abort initialization
        if not self.config['enabled']:
            self.log.debug("SoundSystem: The sound system has been disabled in "
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

        if 'master_volume' not in self.config:
            self.config['master_volume'] = DEFAULT_MASTER_VOLUME

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

        # Set initial master volume level
        self.master_volume = self.config['master_volume']

        # Establish machine tick function callback (will process internal audio events)
        self.clock_event = Clock.schedule_interval(self.tick, 0)

        # Start audio engine processing
        self.audio_interface.enable()
        self._initialized = True

        self.mc.events.add_handler("master_volume_increase", self.master_volume_increase)
        self.mc.events.add_handler("master_volume_decrease", self.master_volume_decrease)
        self.mc.events.add_handler("shutdown", self.shutdown)
        self.mc.events.add_handler("client_connected", self._send_volume, -1)

    def _send_volume(self, **kwargs):
        del kwargs
        self.mc.set_machine_var("master_volume", self.audio_interface.get_master_volume())

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
        self._send_volume()

    @property
    def default_track(self):
        """Return default track."""
        return self.audio_interface.get_track(0)

    def master_volume_increase(self, delta: float=0.05, **kwargs):
        """Increase master volume by delta.

        Args:
            delta: How much to increase volume?
        """
        del kwargs
        self.master_volume += delta
        self.log.info("Increased master volume by %s to %s.", delta, self.master_volume)

    def master_volume_decrease(self, delta: float=0.05, **kwargs):
        """Decrease master volume by delta.

        Args:
            delta: How much to decrease volume?
        """
        del kwargs
        self.master_volume -= delta
        self.log.info("Decreased master volume by %s to %s.", delta, self.master_volume)

    def _create_track(self, name, config=None):
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

        if config is None:
            config = {}

        if 'volume' not in config:
            config['volume'] = DEFAULT_TRACK_VOLUME

        if 'type' not in config:
            config['type'] = 'standard'

        if config['type'] not in ['standard', 'playlist', 'live_loop']:
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
            # TODO: Implement playlist track create
            raise NotImplementedError('Playlist track not yet implemented')

        elif config['type'] == 'live_loop':
            raise NotImplementedError('LiveLoop track not yet implemented')
            # track = self.audio_interface.create_live_loop_track(self.mc, name, config['volume'])

        if track is None:
            raise AudioException("Could not create '{}' track due to an error".format(name))

        self.tracks[name] = track
        
        if 'events_when_stopped' in config and config['events_when_stopped'] is not None:
            track.events_when_stopped = Util.string_to_list(config['events_when_stopped'])

        if 'events_when_played' in config and config['events_when_played'] is not None:
            track.events_when_played = Util.string_to_list(config['events_when_played'])

        if 'events_when_paused' in config and config['events_when_paused'] is not None:
            track.events_when_paused = Util.string_to_list(config['events_when_paused'])

        if 'events_when_resumed' in config and config['events_when_resumed'] is not None:
            track.events_when_resumed = Util.string_to_list(config['events_when_resumed'])
    
    def tick(self, dt):
        """Clock callback function"""
        del dt
        self.audio_interface.process()
