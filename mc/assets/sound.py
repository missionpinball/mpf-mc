from mc.core.assets import AssetClass
from mc.core.audio.audio_interface import AudioInterface


class SoundAsset(AssetClass):
    """
    Sound asset class contains a single sound that may be played using the audio engine.

    Notes:
        It is critical that the AudioInterface be initialized before any Sound assets
        are loaded.  The loading code relies upon having an active audio interface.
    """
    attribute = 'sounds'  # attribute in MC, e.g. self.mc.images
    path_string = 'sounds'  # entry from mpf_mc:paths: for asset folder name
    config_section = 'sounds'  # section in the config files for this asset
    extensions = tuple(AudioInterface.supported_extensions())
    class_priority = 100  # Order asset classes will be loaded. Higher is first.

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)

        # do whatever else you want here. Remove the entire method if you
        # don't need to do anything.

        self._container = None  # holds the actual sound samples in memory

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
    def loaded(self):
        """ Indicates whether or not the sound asset has been loaded into memory """
        return self._container is not None and self._container.loaded()

    @property
    def container(self):
        return self._container

    def _do_load(self):
        # This is the method that's actually called to load the asset from
        # disk. It's called by the loader thread so it's ok to block. However
        # since it is a separate thread, don't update any other attributes.

        # When you're done loading and return, the asset will be processed and
        # the ready loaded attribute will be updated automatically,
        # and anything that was waiting for it to load will be called.

        # Load the sound file into memory
        self._container = AudioInterface.load_sound(self.file)

    def _do_unload(self):
        # This is the method that's called to unload the asset. It's called by
        # the main thread so go nuts, but don't block since it's in the main
        # thread.
        AudioInterface.unload_sound(self._container)
        self._container = None

    def stop(self):
        # TODO: implement the function to stop all playing instances of the sound
        pass

    def play(self, loops=0, priority=0, fade_in=0, volume=1.0, **kwargs):
        # TODO: implement play function
        pass
