from mpf.core.assets import Asset, AssetPool
from mpfmc.core.audio.audio_interface import AudioInterface, AudioException
from kivy.logger import Logger


# ---------------------------------------------------------------------------
#    Default sound asset configuration parameter values
# ---------------------------------------------------------------------------
DEFAULT_VOLUME = 0.5
DEFAULT_PRIORITY = 0
DEFAULT_MAX_QUEUE_TIME = None
DEFAULT_LOOPS = 0
MINIMUM_DUCKING_DURATION = "10ms"


class SoundPool(AssetPool):

    # Be sure the pool group, if you use it, is first in the file ahead of the
    # asset class.

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<SoundPool: {}>'.format(self.name)

    @property
    def sound(self):
        return self.asset


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
        super().__init__(mc, name, file, config)

        self._container = None  # holds the actual sound samples in memory
        self._ducking = None

        # Make sure a legal track name has been specified.  If not, throw an exception
        track = self.machine.sound_system.audio_interface.get_track_by_name(self.config['track'])
        if 'track' not in self.config or track is None:
            Logger.error("SoundAsset: sound must have a valid track name. "
                         "Could not create sound '{}' asset.".format(name))
            raise AudioException("Sound must have a valid track name. "
                                 "Could not create sound '{}' asset".format(name))

        self.track = track

        # Validate sound attributes and provide default values
        if 'volume' in self.config:
            self.config['volume'] = max(min(float(self.config['volume']), 1.0), 0.0)
        else:
            self.config['volume'] = DEFAULT_VOLUME

        if 'priority' in self.config:
            self.config['priority'] = int(self.config['priority'])
        else:
            self.config['priority'] = DEFAULT_PRIORITY

        if 'max_queue_time' not in self.config or self.config['max_queue_time'] is None:
            self.config['max_queue_time'] = DEFAULT_MAX_QUEUE_TIME
        else:
            self.config['max_queue_time'] = AudioInterface.string_to_secs(self.config['max_queue_time'])

        if 'loops' in self.config:
            self.config['loops'] = int(self.config['loops'])
        else:
            self.config['loops'] = DEFAULT_LOOPS

        if 'ducking' in self.config:
            self._ducking = DuckingSettings(self.machine, self.config['ducking'])

            # An attenuation value of exactly 1.0 does absolutely nothing so
            # there is no point in keeping the ducking settings for this
            # sound when attenuation is 1.0.
            if self._ducking.attenuation == 1.0:
                self._ducking = None

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<Sound: {}({}), Loaded={}>'.format(self.name, self.id, self.loaded)

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
    def container(self):
        return self._container

    @property
    def ducking(self):
        return self._ducking

    def do_load(self):
        """Loads the sound asset from disk."""

        # Load the sound file into memory
        self._container = AudioInterface.load_sound(self.file)

    def _do_unload(self):
        """Unloads the asset from memory"""

        AudioInterface.unload_sound(self._container)
        self._container = None

    def is_loaded(self):
        """Called when the asset has finished loading"""
        super().is_loaded()
        Logger.debug("SoundAsset: Loaded {} (Track {})".format(self.name, self.track))


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
            raise AudioException("'ducking.target' must contain a valid audio track name")

        track = mc.sound_system.audio_interface.get_track_by_name(config['target'])
        if track is None:
            raise AudioException("'ducking.target' must contain a valid audio track name")
        self.track = track

        # Delay is optional (defaults to 0, must be >= 0)
        if 'delay' in config:
            self.delay = max(mc.sound_system.audio_interface.string_to_samples(config['delay']), 0)
        else:
            self.delay = 0

        if 'attack' not in config:
            raise AudioException("'ducking.attack' must contain a valid attack value (time "
                                 "string or number of samples)")
        self.attack = max(mc.sound_system.audio_interface.string_to_samples(config['attack']),
                          mc.sound_system.audio_interface.string_to_samples(MINIMUM_DUCKING_DURATION))

        if 'attenuation' not in config:
            raise AudioException("'ducking.attenuation' must contain valid attenuation "
                                 "value (0.0 to 1.0)")
        self.attenuation = min(max(float(AudioInterface.string_to_gain(config['attenuation'])), 0.0), 1.0)

        if 'release_point' not in config:
            raise AudioException("'ducking.release_point' must contain a valid release point "
                                 "value (time string or number of samples)")
        # Release point cannot be negative (must be before or at the end of the sound)
        self.release_point = max(mc.sound_system.audio_interface.string_to_samples(config['release_point']), 0)

        if 'release' not in config:
            raise AudioException("'ducking.release' must contain a valid release "
                                 "value (time string or number of samples)")
        self.release = max(mc.sound_system.audio_interface.string_to_samples(config['release']),
                           mc.sound_system.audio_interface.string_to_samples(MINIMUM_DUCKING_DURATION))
