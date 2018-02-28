#!python
#cython: embedsignature=True, language_level=3

import logging

from mpfmc.config_collections.playlist import PlaylistInstance
from mpfmc.assets.sound import SoundInstance
from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.audio.track cimport *


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

        # Dictionary of PlaylistInstance class objects keyed by playlist names
        self._playlist_instances = dict()
        self._playlists_by_sound_instance = dict()

        # Keep track of current and previous playlist
        self._current_playlist = None

        self.log.debug("Created PlaylistController %s: ", self._track.name)

        # Create event handlers for sound instance events
        self.mc.events.add_handler(self.name.lower() + '_playlist_sound_stopped',
                                   self._on_sound_instance_stopped)
        self.mc.events.add_handler(self.name.lower() + '_playlist_sound_about_to_finish',
                                   self._on_sound_instance_about_to_finish)

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
            return

        # TODO: Special behavior needed if specified playlist is already playing (or finishing/fading)

        # Determine settings (override playlist with player settings)
        playlist_instance = PlaylistInstance(playlist,
                                             self.mc.playlists[playlist],
                                             self.crossfade_time,
                                             context,
                                             player_settings)

        self._playlist_instances[playlist] = { 'playlist': playlist_instance, 'sound_instances': [] }

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

            events_when_stopped = [self.name.lower() + '_playlist_sound_stopped']
            if sound.events_when_stopped:
                events_when_stopped.extend(sound.events_when_stopped)

            events_when_about_to_finish = [self.name.lower() + '_playlist_sound_about_to_finish']
            if sound.events_when_about_to_finish:
                events_when_about_to_finish.extend(sound.events_when_about_to_finish)

            # Play sound on playlist track (override certain settings needed to manage playlist)
            # Standard track will return a sound instance if play was successful
            sound_instance = self._track.play_sound(sound,
                                                    context,
                                                    {
                                                        'fade_in': 0.0,
                                                        'fade_out': 0.0,
                                                        'about_to_finish_time': playlist_instance.crossfade_time,
                                                        'max_queue_time': None,
                                                        'events_when_stopped': events_when_stopped,
                                                        'events_when_about_to_finish': events_when_about_to_finish
                                                    })

            # Associate sound instance with playlist instance
            self._playlist_instances[playlist_instance.name]['sound_instances'].append(sound_instance)
            self._playlists_by_sound_instance[sound_instance] = playlist_instance

        pass

    def stop(self):
        """Immediately stop the currently playing playlist. Will fade out using the crossfade setting."""
        pass

    def advance(self):
        """Advance the currently playing playlist to the next sound."""

        # If there is no current playlist, do nothing
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

    def _play_sound(self):
        pass

    def _on_sound_instance_stopped(self, sound_instance=None, **kwargs):
        """Callback function called whenever a playlist sound has finished playing."""

        if sound_instance is None:
            return

        if sound_instance not in self._playlists_by_sound_instance:
            return

        # Get playlist for sound_instance
        playlist = self._playlists_by_sound_instance[sound_instance]

        # TODO: Determine if playlist has finished. If so, send events
        # Playlist is finished when last sound instance of playlist has completed

    def _on_sound_instance_about_to_finish(self, sound_instance=None, **kwargs):
        """Callback function called whenever a playlist sound is about to finish playing."""
        
        if sound_instance is None:
            return

        if sound_instance not in self._playlists_by_sound_instance:
            return

        # Get playlist for sound_instance
        playlist = self._playlists_by_sound_instance[sound_instance]

        # Determine if this is the last sound in the playlist
        if playlist.end_of_playlist and not playlist.repeat:
            return

        # Advance to the next sound in the playlist
        self.advance()


