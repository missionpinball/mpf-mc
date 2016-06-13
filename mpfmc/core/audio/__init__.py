"""
Audio module provides all the audio features (playing of sounds) for the media controller.
"""

from kivy.clock import Clock
from mpfmc.core.audio.audio_interface import AudioInterface, AudioException, Track
import logging

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


class SoundSystem(object):
    """
    The SoundSystem class is used to read the sound system settings from the
    config file and then initialize the audio interface and create the
    specified tracks.
    """

    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('SoundSystem')
        self._initialized = False
        self.audio_interface = None
        self.config = {}
        self.tracks = {}
        self.sound_events = {}

        self.log.debug("Loading the Sound System")

        # Load configuration for sound system
        if 'sound_system' not in self.mc.machine_config:
            self.log.info("SoundSystem: Using default 'sound_system' settings")
            self.config = {}
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
            self.audio_interface = AudioInterface.initialize(
                mc=self.mc,
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

        # Set initial master volume level
        self.master_volume = self.config['master_volume']

        # Establish machine tick function callback (will process internal audio events)
        Clock.schedule_interval(self.tick, 0)

        # Establish event callback functions
        # Setup event triggers (sound events trigger BCP triggers)

        # Start audio engine processing
        self.audio_interface.enable()
        self._initialized = True

    @property
    def enabled(self):
        return self._initialized

    @property
    def master_volume(self):
        return self.audio_interface.get_master_volume()

    @master_volume.setter
    def master_volume(self, value):
        # Constrain volume to the range 0.0 to 1.0
        value = min(max(value, 0.0), 1.0)
        self.audio_interface.set_master_volume(value)

    @property
    def default_track(self):
        return self.audio_interface.get_track(0)

    def master_volume_increase(self):
        # TODO: Implement me
        pass

    def master_volume_decrease(self):
        # TODO: Implement me
        pass

    def _create_track(self, name, config=None):
        """
        Creates a track in the audio system with the specified name and configuration.

        Args:
            name: The track name (which will be used to reference the track, such as
                "voice" or "sfx".
            config: A Python dictionary containing the configuration settings for
                this track.

        Returns:
            True if the track was successfully created, False otherwise
        """
        if self.audio_interface is None:
            self.log.error("Could not create '%s' track - the audio interface has "
                           "not been initialized", name)
            return False

        # Validate track config parameters
        if name in self.tracks:
            self.log.error("Could not create '%s' track - a track with that name "
                           "already exists", name)
            return False

        if config is None:
            config = {}

        if 'simultaneous_sounds' not in config:
            config['simultaneous_sounds'] = DEFAULT_TRACK_MAX_SIMULTANEOUS_SOUNDS

        if 'volume' not in config:
            config['volume'] = DEFAULT_TRACK_VOLUME

        # Create the track
        track = self.audio_interface.create_track(name,
                                                  config['simultaneous_sounds'],
                                                  config['volume'])
        if track is None:
            return False

        self.tracks[name] = track
        return True

    def sound_loaded_callback(self):
        pass

    def tick(self, dt):
        del dt
        self.audio_interface.process()
