"""
Audio module provides all the audio features (playing of sounds) for the media controller.
"""

from kivy.logger import Logger
from mc.core.audio.audio_interface import AudioInterface, AudioException, Track, Sound

__all__ = ('SoundController', )


class SoundController(object):

    def __init__(self, mc):
        self.mc = mc

        # The sounds dictionary contains all sounds specified in the config files keyed by name.
        # The actual audio data will be managed by the PinAudio extension library.  The sounds
        # dictionary can also contain sound groups, which are groupings of sound that are
        # referenced just like an individual sound.
        self.sounds = {}

        # The tracks dictionary contains the audio tracks used in the sound system.  Each track
        # is essentially an audio channel with it's own properties that corresponds to its own
        # mixer channel in the PinAudio sound library.  Tracks are keyed by name.
        self.tracks = {}

        self._master_volume = 1.0

        # TODO: Here is a list of processing steps/features to implement
        # Load configuration for sound engine and sound assets

        # Initialize audio interface library (get audio output)
        try:
            self.audio_interface = AudioInterface.initialize()
        except AudioException:
            Logger.error("SoundController: Could not initialize the audio interface. "
                         "Audio features will not be available.")
            self.audio_interface = None

        # Setup tracks/mixer channels (including initial volume levels)
        # Establish machine tick function callback (calls PinAudio process_event_callbacks fn)
        # Establish event callback functions
        # Setup sounds
        # Load sound assets
        # Setup event triggers (sound events trigger BCP triggers)
        # Start mixer channels processing
        #

    @property
    def master_volume(self):
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value):
        # Constrain volume to the range 0.0 to 1.0
        value = max(min(value, 1.0), 0.0)
        self._master_volume = value

    def _create_track(self, name, max_simultaneous_sounds, volume=1.0):
        if self.audio_interface is None:
            return False

        if name in self.tracks:
            Logger.error("SoundController: Could not create '{}' track - a track with that name already exists"
                         .format(name))
            return False

        track = self.audio_interface.create_track(name, max_simultaneous_sounds, volume)
        if track is None:
            return False

        self.tracks[name] = track
        return True


