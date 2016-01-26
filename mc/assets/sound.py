from mc.core.assets import Asset, AssetPool
from mc.core.audio.audio_interface import AudioInterface, AudioException
from kivy.logger import Logger


# ---------------------------------------------------------------------------
#    Default sound asset configuration parameter values
# ---------------------------------------------------------------------------
DEFAULT_VOLUME = 0.5
DEFAULT_MAX_QUEUE_TIME = None
DEFAULT_LOOPS = 0


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

        # Make sure a legal track name has been specified.  If not, throw an exception
        track = self.mc.sound_system.audio_interface.get_track_by_name(self.config['track'])
        if 'track' not in self.config or track is None:
            Logger.error("SoundAsset: sound must have a valid track name. "
                         "Could not create sound '{}' asset.".format(name))
            raise AudioException("Sound must have a valid track name. "
                                 "Could not create sound '{}' asset".format(name))

        self.track = track

        if 'volume' not in self.config:
            self.config['volume'] = DEFAULT_VOLUME

        if 'max_queue_time' not in self.config or self.config['max_queue_time'] is None:
            self.config['volume'] = DEFAULT_MAX_QUEUE_TIME

        if 'loops' not in self.config:
            self.config['loops'] = DEFAULT_LOOPS

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

    def _do_load(self):
        # This is the method that's actually called to load the asset from disk.

        # Load the sound file into memory
        self._container = AudioInterface.load_sound(self.file)

    def _do_unload(self):
        # This is the method that's called to unload the asset.
        AudioInterface.unload_sound(self._container)
        self._container = None

    def _loaded(self):
        super()._loaded()
        Logger.debug("SoundAsset: Loaded {} (Track {})".format(self.name, self.track))

