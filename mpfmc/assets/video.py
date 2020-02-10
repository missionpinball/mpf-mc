from kivy.properties import AliasProperty

from mpf.core.assets import AssetPool
from mpf.core.config_validator import ConfigValidator
from mpfmc.assets.mc_asset import McAsset
from mpfmc.core.video import Video
from mpfmc.assets.sound import DuckingSettings
from urllib.request import pathname2url
from os.path import realpath
import sys
import logging


class VideoPool(AssetPool):

    def __repr__(self):
        return '<VideoPool: {}>'.format(self.name)

    @property
    def video(self):
        return self.asset


class VideoAsset(McAsset):
    attribute = 'videos'
    path_string = 'videos'
    config_section = 'videos'
    extensions = ('mkv', 'avi', 'mpg', 'mp4', 'm4v', 'mov')
    class_priority = 100
    pool_config_section = 'video_pools'
    asset_group_class = VideoPool

    def __init__(self, mc, name, file, config):
        self.log = logging.getLogger('VideoAsset')
        self._video = None
        self._ducking = None
        super().__init__(mc, name, file, config)

        # Custom video player alpha channel support is controlled by config setting
        if 'alpha_channel' in config:
            self._alpha_channel = config['alpha_channel']
        else:
            self._alpha_channel = False

        if self._alpha_channel:
            self.log.debug("The '{}' video has been configured with alpha channel support. "
                           "Please ensure the video was encoded using a codec that supports "
                           "an alpha channel.".format(name))

        # Setup events to post when video state changes
        self._events_when_played = list()
        self._events_when_stopped = list()

        if self.config['events_when_played']:
            self._events_when_played = self.config['events_when_played']

        if self.config['events_when_stopped']:
            self._events_when_stopped = self.config['events_when_stopped']

        self._mute_audio = self.config.get('mute_audio', False)
        if self._mute_audio:
            self.log.debug("NOTICE: The '{}' video has been configured to mute audio "
                           "(video will play with no sound)".format(name))

        # Ducking only applies when the sound system is enabled and video sound
        # is integrated with the audio system
        if self.machine.sound_system and self.machine.sound_system.enabled and \
                self.machine.sound_system.integrated_video_sound and \
                'ducking' in self.config:
            try:
                ducking_config = ConfigValidator.validate_config("sounds:ducking", self.config['ducking'])
                self._ducking = DuckingSettings(self.machine, ducking_config)
            except Exception:
                raise Exception("Error in ducking settings: {}, Could not create video '{}' asset"
                                .format(sys.exc_info()[1], self.name))

        # An attenuation value of exactly 1.0 does absolutely nothing so
        # there is no point in keeping the ducking settings for this
        # sound when attenuation is 1.0.
        if self._ducking and self._ducking.attenuation == 1.0:
            self._ducking = None

    @property
    def alpha_channel(self):
        return self._alpha_channel

    def do_load(self):
        # For videos, we need them to load in the main thread, so we do not
        # load them here and load them via is_loaded() below.
        pass

    def is_loaded(self):
        """Handle that asset has been loaded."""
        self._video = Video(filename=self.file,
                            alpha_channel=self.alpha_channel,
                            av_offset=self.machine.sound_system.av_offset,
                            mute_audio=self._mute_audio)
        self._video.load()
        self._check_duration(None)
        self._video.bind(on_play=self.on_play,
                         on_stop=self.on_stop)

        # Connect video to audio track (if sound system is managing video audio)
        if self.machine.sound_system.integrated_video_sound:
            video_audio_track = self.machine.sound_system.audio_interface.get_track_by_name("video")
            if video_audio_track:
                video_audio_track.connect_video(self.name, self._video.video)

        self.loading = False
        self.loaded = True
        self.unloading = False

        self._call_callbacks()

    def _do_unload(self):
        if self._video:
            self._video.stop()

            # Disconnect video from audio track (if sound system is managing video audio)
            if self.machine.sound_system.integrated_video_sound:
                video_audio_track = self.machine.sound_system.audio_interface.get_track_by_name("video")
                if video_audio_track:
                    video_audio_track.disconnect_video(self.name)

            self._video.unload()
            self._video = None

    def set_end_behavior(self, eos='stop'):
        if self._video:
            assert eos in ('loop', 'pause', 'stop')
            self._video.eos = eos

    def _check_duration(self, instance):
        del instance
        if self._video and self._video.duration <= 0:
            raise ValueError(
                "Video file {} was loaded, but seems to have no content. Check"
                " to make sure you have the proper Gstreamer plugins for the "
                "codec this video needs".format(self.file))

    def on_play(self, *args):
        del args

        if self._events_when_played:
            for event in self._events_when_played:
                self.machine.post_mc_native_event(event)

    def on_stop(self, *args):
        del args

        if self._events_when_stopped:
            for event in self._events_when_stopped:
                self.machine.post_mc_native_event(event)

    #
    # Properties
    #

    @property
    def video(self):
        return self._video

    @property
    def texture(self):
        return self._video.texture

    @property
    def position(self):
        try:
            return self._video.position
        except AttributeError:
            return 0

    @position.setter
    def position(self, pos):
        # position in secs
        try:
            self._video.position = pos  # noqa
        except AttributeError:
            pass

    @property
    def duration(self):
        try:
            return self._video.duration
        except AttributeError:
            return 0

    @property
    def volume(self):
        try:
            return self._video.volume
        except AttributeError:
            return 0

    @volume.setter
    def volume(self, volume):
        # float 0.0 - 1.0
        try:
            self._video.volume = volume  # noqa
        except AttributeError:
            pass

    @property
    def state(self):
        if self._video:
            return self._video.state
        else:
            return ''
