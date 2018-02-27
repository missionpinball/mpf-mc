#!python
#cython: embedsignature=True, language_level=3

import logging
from mpfmc.core.audio.track cimport *
from mpfmc.config_collections.playlist import PlaylistInstance
from mpfmc.assets.sound import SoundInstance


# ---------------------------------------------------------------------------
#    PlaylistController class
# ---------------------------------------------------------------------------
cdef class PlaylistController:
    """
    PlaylistController class
    """

    def __init__(self, object mc, object track, float crossfade_time=0.0, float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            track: The audio track that will be managed by this playlist controller
            crossfade_time: The default crossfade time (secs) to use when fading between sounds
            volume: The track volume (0.0 to 1.0)
        """
        self.log = logging.getLogger("PlaylistController")
        self.mc = mc
        self._track = track
        self._crossfade_time = crossfade_time

        # Dictionary of SoundInstance class objects keyed by SoundInstance.id
        self._playing_sound_instances_by_id = dict()
        self._playlist_instances_by_sound_instance_id = dict()

        # Keep track of current and previous playlist
        self._current_playlist = None
        self._current_playlist_ending = False
        self._previous_playlist = None

        self.log.debug("Created PlaylistController %s: ", self._track.name)

    def __dealloc__(self):
        """Destructor"""
        pass

    def __repr__(self):
        return '<PlaylistController.{}>'.format(self.name)

    @property
    def name(self):
        """The name of the playlist controller (and corresponding track)"""
        return self._track.name

    @property
    def crossfade_time(self):
        """The time (secs) to use when fading between sounds"""
        return self._crossfade_time

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the playlist track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        self._track.stop_all_sounds(fade_out_seconds)

        # TODO: playlist housekeeping (stopped events, remove instance, etc.)

    def play(self, dict playlist not None, str context=None, dict player_settings=None):
        """
        Immediately play a playlist.

        Args:
            playlist: The playlist asset object to play.
            context: The calling context (if any)
            player_settings: Settings to use for playback
        """

        self.log.debug("play - Preparing playlist '%s' for playback.", playlist)

        if player_settings is None:
            player_settings = dict()

        # Determine settings (override playlist with player settings)
        playlist_instance = PlaylistInstance(playlist, self.crossfade_time, context, player_settings)

        # Is there already a playlist playing?
        if self._current_playlist:
            # Already a playlist playing

            # Is there already a previous playlist that is still active (fading)?
            if self._previous_playlist:
                # TODO: need mechanism to delay new playlist until previous is finished
                # Set a callback function on previous playlist completion?
                pass

            pass
        else:
            # No playlist playing
            self._current_playlist = playlist_instance

            # Get next sound to play from playlist
            sound_name = self._current_playlist.get_next_sound_name()

            # Create sound instance
            sound = self.mc.sounds[sound_name]
            sound_instance = SoundInstance(sound,
                                           context,
                                           {
                                               'about_to_finish_time': self._current_playlist.crossfade_time,
                                               'fade_in': 0.0,
                                               'fade_out': self._current_playlist.crossfade_time
                                           })

            # Assign sound instance to idle sound player
            # Save sound instance to active sound list

        pass

    def stop_playlist(self):
        """Immediately stop the currently playing playlist. Will fade out using the crossfade setting."""
        pass

    def advance_playlist(self):
        """Advance the currently playing playlist to the next sound."""

        # If no playlist is playing, do nothing
        if not self._current_playlist:
            return

        # Determine if playlist will now repeat/loop.  Post playlist looping events (if necessary)
        if self._current_playlist.end_of_playlist:
            if self._current_playlist.repeat and self._current_playlist.events_when_looping:
                    for event in self._current_playlist.events_when_looping:
                        self.mc.post_mc_native_event(event)

        # Set the next sound in the sound player and calculate the fades based on the crossfade setting
        next_sound_name = self._current_playlist.get_next_sound_name()
        if next_sound_name:
            pass
        else:
            self._current_playlist_ending = True

