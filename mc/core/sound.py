
import logging
import abc
from queue import PriorityQueue

from pinaudio import get_audio_output


class SoundController(object):

    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('SoundController')

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

    @property
    def master_volume(self):
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value):
        # Constrain volume to the range 0.0 to 1.0
        if value > 1.0:
            value = 1.0
        elif value < 0.0:
            value = 0.0

        self._master_volume = value


class SoundInterface(metaclass=abc.ABCMeta):
    """
    SoundInterface is an abstract base class that defines the interface to interact with sound
    objects (play, stop, load, unload, etc.) in the Sound Controller.
    """
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @abc.abstractclassmethod
    def play(self, track=None):
        pass

    @abc.abstractclassmethod
    def load(self):
        pass

    @abc.abstractclassmethod
    def unload(self):
        pass


class Sound(SoundInterface):
    """
    The Sound class represents a single sound file asset to be used in the media controller.
    """
    def __init__(self, name):
        super().__init__(name)

        self._sound_number = 0

    def play(self, track=None):
        pass

    def load(self):
        pass

    def unload(self):
        pass


class SoundGroup(SoundInterface):
    """
    The SoundGroup class represents a single sound group which allows for referencing a group
    of sound variations as if it were a single sound.  They can be used for random differences
    in a sound (such as slight variations of a slingshot sound) or for an ordered progression
    of sounds that will repeat. Random sounds from a group can also be triggered via sound
    groups.
    """
    def __init__(self, name):
        super().__init__(name)

    def play(self, track=None):
        pass

    def load(self):
        pass

    def unload(self):
        pass


class Playlist(SoundInterface):
    """
    The Playlist class represents a single sound playlist which allows for multiple sounds
    to be played one right after another.  There are also several looping features available in
    playlists.
    """
    def __init__(self, name):
        super().__init__(name)

    def play(self, track=None):
        pass

    def load(self):
        pass

    def unload(self):
        pass


class Track(object):
    """
    A Track is essentially an audio channel with it's own properties that corresponds to its own
    mixer channel in the PinAudio sound library.
    """

    def __init__(self, name, max_simultaneous_sounds, volume=0.5):
        """
        Initializer
        Args:
            name: The track name.
            max_simultaneous_sounds: The number of sounds that may be played at the same time on the track.
            volume: The track volume (0.0 to 1.0)
        """
        self._name = name
        self._max_simultaneous_sounds = max_simultaneous_sounds
        self._volume = 0

        # Number corresponding to the number of the mixer channel in the PinAudio sound library
        # that this track is managing.
        self._mixer_channel_number = -1

        # The play queue will manage a sound playback 'wait list' for handling sound play requests
        # when the track is already at playback capacity.
        self.play_queue = PriorityQueue()

        self.volume = volume

    @property
    def name(self):
        """ The track name. """
        return self._name

    @property
    def max_simultaneous_sounds(self):
        """ The number of sounds that may be played simultaneously on this track. """
        return self._max_simultaneous_sounds

    @property
    def volume(self):
        """ The volume (0.0 to 1.0) of this track. """
        return self._volume

    @volume.setter
    def volume(self, value):
        """ Sets the volume (0.0 to 1.0) of this track. """
        # Constrain volume to the range 0.0 to 1.0
        if value > 1.0:
            value = 1.0
        elif value < 0.0:
            value = 0.0

        self._volume = value

