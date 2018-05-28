#!python
#cython: embedsignature=True, language_level=3

import logging
from functools import partial

from mpfmc.config_collections.playlist import PlaylistInstance
from mpfmc.core.audio.track cimport *


# ---------------------------------------------------------------------------
#    PlaylistController class
# ---------------------------------------------------------------------------
class PlaylistController:
    """
    PlaylistController class
    """

    def __init__(self, object mc, object track, float crossfade_time=0.0, float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            track: The audio track that will be managed by this playlist controller (standard track)
            crossfade_time: The default crossfade time (secs) to use when fading between sounds
            volume: The playlist volume (0.0 to 1.0)
        """
        self.log = logging.getLogger("PlaylistController")
        self.mc = mc
        self._track = track
        self._crossfade_time = crossfade_time

        # Dictionary of PlaylistInstance class objects keyed by SoundInstance ID
        self._playlists_by_sound_instance = dict()

        # Keep track of current and previous playlist
        self._current_playlist = None

        # Keeps track of a pending request that cannot be immediately serviced because the
        # underlying audio track is busy (only 2 players)
        self._pending_request = None

        # Create event handlers for sound instance events
        # Note: we don't have to worry about played events since the playlist controller will initiate
        # playback and therefore will already know when those events are occurring.
        self.mc.events.add_handler('{}_playlist_sound_stopped'.format(self.name.lower()),
                                   self._on_sound_instance_stopped, 0)
        self.mc.events.add_handler('{}_playlist_sound_about_to_finish'.format(self.name.lower()),
                                   self._on_sound_instance_about_to_finish)

        self.log.debug("Created PlaylistController %s: ", self._track.name)

    def __dealloc__(self):
        """Destructor"""
        pass

    def __repr__(self):
        return '<PlaylistController.{}>'.format(self.name)

    @property
    def name(self):
        """The name of the playlist controller (and corresponding audio track)"""
        return self._track.name

    @property
    def track(self):
        """The corresponding audio track the playlist is managing"""
        return self._track

    @property
    def crossfade_time(self):
        """The time (secs) to use when fading between sounds"""
        return self._crossfade_time

    @property
    def has_pending_request(self):
        """Whether the playlist controller has a pending request queued until it is not busy"""
        return self._pending_request is not None

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the playlist track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        self._track.stop_all_sounds(fade_out_seconds)

        # TODO: playlist housekeeping (stopped events, remove instance, etc.)

    def play(self, str playlist not None, str context=None, dict player_settings=None):
        """
        Immediately play a playlist.

        Args:
            playlist: The name of the playlist asset object to play.
            context: The calling context (if any)
            player_settings: Settings to use for playback
        """

        self.log.debug("play - Preparing playlist '%s' for playback.", playlist)

        if player_settings is None:
            player_settings = dict()

        if playlist not in self.mc.playlists:
            self.log.error("PlaylistController (%s track): Could not play specified playlist "
                           "(%s) as it does not exist", self.name, playlist)
            return None

        # Is there already a previous playlist that is still active (fading)?
        if self._is_busy():
            # Delay play playlist until track is finished with current crossfade (too busy)
            self._pending_request = partial(self.play, playlist=playlist, context=context,
                                            player_settings=player_settings)

            self.log.debug("play - Playlist track is too busy. Delaying play playlist call.")
            return None

        # Determine settings (override playlist with player settings)
        playlist_instance = PlaylistInstance(playlist,
                                             self.mc.playlists[playlist],
                                             self.crossfade_time,
                                             context,
                                             player_settings)

        # Is there already a playlist playing?
        if self._current_playlist:
            # Already a playlist playing.  We know there is at least one free sound player because
            # of the _is_busy() call above.
            # Stop the current playlist
            self.stop()

        # Start the new playlist (now becomes the current playlist)
        self._current_playlist = playlist_instance

        # Post events when played for playlist
        for event in self._current_playlist.events_when_played:
            self.mc.post_mc_native_event(event)

        # Get the next sound to play from playlist
        sound_name = self._current_playlist.get_next_sound_name()
        self._play_playlist_sound(sound_name, self._current_playlist)

        return playlist_instance

    def _is_busy(self):
        """Returns whether or not all the sound players for the playlist track are currently busy"""
        if self._track.get_sound_players_in_use_count() > 1:
            return True
        else:
            return False

    def _play_playlist_sound(self, str sound_name, object playlist, float fade_in=0.0):
        """
        Plays the specified playlist sound
        Args:
            sound_name: The name of the sound to start playing
            playlist: The playlist from which the sound came from
            fade_in: The number of seconds over which to fade in the sound (frequently the
                crossfade time).

        """

        # Create sound instance
        sound = self.mc.sounds[sound_name]

        # Add custom events to post when particular sound actions occur (stop, about to finish).
        # These events are used to trigger playlist events (advance, stop)
        events_when_stopped = []
        if sound.events_when_stopped:
            events_when_stopped.extend(sound.events_when_stopped)
        events_when_stopped.extend(['{}_playlist_sound_stopped'.format(self.name.lower())])

        events_when_about_to_finish = []
        if sound.events_when_about_to_finish:
            events_when_about_to_finish.extend(sound.events_when_about_to_finish)
        events_when_about_to_finish.extend(['{}_playlist_sound_about_to_finish'.format(self.name.lower())])

        # Post events when sound changed as a new sound is playing now for the current playlist
        for event in self._current_playlist.events_when_sound_changed:
            self.mc.post_mc_native_event(event)

        # Play sound on playlist track (override certain settings needed to manage playlist)
        # Standard track will return a sound instance if play was successful
        sound_instance = self._track.play_sound(sound,
                                                playlist.context,
                                                {
                                                    'fade_in': fade_in,
                                                    'fade_out': 0.0,
                                                    'about_to_finish_time': playlist.crossfade_time,
                                                    'max_queue_time': None,
                                                    'events_when_stopped': events_when_stopped,
                                                    'events_when_about_to_finish': events_when_about_to_finish
                                                })

        # Associate sound instance with playlist instance
        self._playlists_by_sound_instance[sound_instance] = playlist
        playlist.current_sound_instance = sound_instance

    def stop(self):
        """Immediately stop the currently playing playlist. Will fade out using the crossfade setting."""
        if not self._current_playlist:
            self.log.debug("stop - No playlist is currently playing. Could not stop current playlist.")
            return

        self.log.debug("stop - Stopping the current playlist ('%s').",
                       self._current_playlist.name)

        # Stop the current sound (if another sound is fading out, let it finish on its own)
        if self._current_playlist.current_sound_instance:
            self._track.stop_sound_instance(self._current_playlist.current_sound_instance,
                                            self._current_playlist.crossfade_time)

        self._current_playlist = None

    def advance(self):
        """Advance the currently playing playlist to the next sound."""

        # If there is no current playlist, do nothing
        if not self._current_playlist:
            self.log.debug("advance - No playlist is currently playing. Could not advance to next sound")
            return

        self.log.debug("advance - Advancing the current playlist ('%s') to the next sound.",
                       self._current_playlist.name)

        if self._is_busy():
            # Delay advance playlist until track is finished with current crossfade (too busy)
            self._pending_request = partial(self.advance)
            self.log.debug("advance - Playlist track is too busy. Delaying advance to next sound")
            return

        # Determine if playlist will now repeat/loop.  Post playlist looping events (if necessary)
        if self._current_playlist.end_of_playlist:
            if self._current_playlist.repeat and self._current_playlist.events_when_looping:
                    for event in self._current_playlist.events_when_looping:
                        self.mc.post_mc_native_event(event)

        # Set the next sound in the sound player and calculate the fades based on the crossfade setting
        next_sound_name = self._current_playlist.get_next_sound_name()
        if next_sound_name:
            if self._current_playlist.current_sound_instance is not None:
                self._track.stop_sound_instance(self._current_playlist.current_sound_instance,
                                                self._current_playlist.crossfade_time)
                self._current_playlist.fading_sound_instance = self._current_playlist.current_sound_instance

            self._play_playlist_sound(next_sound_name, self._current_playlist, self._current_playlist.crossfade_time)

    def set_repeat(self, repeat=True):
        """Set whether or not the currently playing playlist should repeat when finished."""

        if self._current_playlist:
            self._current_playlist.loop = repeat
            self.log.debug("set_repeat - Setting repeat for currently playlist to {}.", str(repeat))
        else:
            self.log.debug("set_repeat - No playlist is currently playing. "
                           "Could not set repeat to {}.", str(repeat))

    def _on_sound_instance_stopped(self, sound_instance=None, **kwargs):
        """Callback function called whenever a playlist sound has finished playing."""

        if sound_instance is None or sound_instance not in self._playlists_by_sound_instance:
            return

        # Get playlist for sound_instance and remove it from dictionary of active sounds
        playlist = self._playlists_by_sound_instance[sound_instance]
        del self._playlists_by_sound_instance[sound_instance]

        if playlist.current_sound_instance == sound_instance:
            playlist.current_sound_instance = None
        if playlist.fading_sound_instance == sound_instance:
            playlist.fading_sound_instance = None

        # Post events when sound stopped for playlist
        for event in playlist.events_when_sound_stopped:
            self.mc.post_mc_native_event(event)

        # Playlist is finished when last sound instance of playlist has completed
        if playlist not in self._playlists_by_sound_instance.values():

            # Playlist has stopped

            # Trigger any stopped events
            if playlist.events_when_stopped is not None:
                for event in playlist.events_when_stopped:
                    self.mc.post_mc_native_event(event)

            if playlist == self._current_playlist:
                self._current_playlist = None

        # Service any pending request (play, advance)
        if self._pending_request:
            request = self._pending_request
            self._pending_request = None
            request()

    def _on_sound_instance_about_to_finish(self, sound_instance=None, **kwargs):
        """Callback function called whenever a playlist sound is about to finish playing."""

        if sound_instance is None or sound_instance not in self._playlists_by_sound_instance:
            return

        # Get playlist for sound_instance
        playlist = self._playlists_by_sound_instance[sound_instance]

        # Take no action if the sound is not from the current playlist
        if playlist != self._current_playlist:
            return

        # Determine if this is the last sound in the playlist
        if playlist.end_of_playlist and not playlist.repeat:
            return

        # Advance to the next sound in the playlist
        self.advance()

    def clear_context(self, context):
        """
        Stops the current playlist if it was played from the specified context.

        Args:
            context: The context to clear
        """
        self.log.debug("Clearing context %s", context)

        if self._current_playlist and self._current_playlist.context == context:
            self.stop()

        # Also need to check if there is a pending request to play another playlist with
        # the specified context.  If so, delete the pending request.
        if self._pending_request and "context" in self._pending_request.keywords and \
                self._pending_request.keywords["context"] == context:
            self._pending_request = None
