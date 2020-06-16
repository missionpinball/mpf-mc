#!python
#cython: embedsignature=True, language_level=3

from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
import cython
import logging
import time
from math import ceil
from heapq import heappush, heappop, heapify

from mpfmc.assets.sound import SoundInstance, SoundStealingMethod
from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.inline cimport lerpU8, in_out_quad
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.track_standard cimport *
from mpfmc.core.audio.audio_exception import AudioException


# ---------------------------------------------------------------------------
#    Settings
# ---------------------------------------------------------------------------

# The maximum number of consecutive null buffers to receive while streaming before
# terminating the sound (will cause drop outs)
DEF CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT = 2


# ---------------------------------------------------------------------------
#    TrackStandard class
# ---------------------------------------------------------------------------
cdef class TrackStandard(Track):
    """
    Track class
    """

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            max_simultaneous_sounds: The maximum number of sounds that can be played simultaneously
                on the track
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackStandard." + name)

        SDL_LockAudio()

        # Dictionary of SoundInstance class objects keyed by SoundInstance.id
        self._playing_instances_by_id = dict()

        # Priority queue of SoundInstance objects waiting to be played
        self._sound_queue = list()

        # Set track type specific settings
        self.state.mix_callback_function = TrackStandard.mix_playing_sounds

        # Allocate memory for the specific track type state struct (TrackStandardState)
        self.type_state = <TrackStandardState*> PyMem_Malloc(sizeof(TrackStandardState))
        self.state.type_state = <void*>self.type_state

        # Make sure the number of simultaneous sounds is within the allowable range
        if max_simultaneous_sounds > MAX_SIMULTANEOUS_SOUNDS_LIMIT:
            self.log.warning("The maximum number of simultaneous sounds per track is %d",
                             MAX_SIMULTANEOUS_SOUNDS_LIMIT)
            max_simultaneous_sounds = MAX_SIMULTANEOUS_SOUNDS_LIMIT
        elif max_simultaneous_sounds < 1:
            self.log.warning("The minimum number of simultaneous sounds per track is 1")
            max_simultaneous_sounds = 1
        self._max_simultaneous_sounds = max_simultaneous_sounds
        self.type_state.sound_player_count = max_simultaneous_sounds

        # Allocate memory for the sound player structs needed for the desired number of
        # simultaneous sounds that can be played on the track.
        self.type_state.sound_players = <SoundPlayer*> PyMem_Malloc(self.type_state.sound_player_count * sizeof(SoundPlayer))

        # Initialize sound player attributes
        for i in range(self.type_state.sound_player_count):
            self.type_state.sound_players[i].status = player_idle
            self.type_state.sound_players[i].track_num = self.number
            self.type_state.sound_players[i].number = i
            self.type_state.sound_players[i].current.sample = NULL
            self.type_state.sound_players[i].current.loops_remaining = 0
            self.type_state.sound_players[i].current.current_loop = 0
            self.type_state.sound_players[i].current.volume = 0
            self.type_state.sound_players[i].current.sample_pos = 0
            self.type_state.sound_players[i].current.loop_start_pos = 0
            self.type_state.sound_players[i].current.loop_end_pos = 0
            self.type_state.sound_players[i].current.sound_id = 0
            self.type_state.sound_players[i].current.sound_instance_id = 0
            self.type_state.sound_players[i].current.sound_priority = 0
            self.type_state.sound_players[i].current.fading_status = fading_status_not_fading
            self.type_state.sound_players[i].current.about_to_finish_marker = no_marker
            self.type_state.sound_players[i].current.sound_has_ducking = False
            self.type_state.sound_players[i].current.ducking_stage = ducking_stage_idle
            self.type_state.sound_players[i].current.ducking_control_points = g_array_sized_new(False, False, sizeof(guint8), CONTROL_POINTS_PER_BUFFER)
            self.type_state.sound_players[i].current.marker_count = 0
            self.type_state.sound_players[i].current.markers = g_array_new(False, False, sizeof(guint))
            self.type_state.sound_players[i].next.sample = NULL
            self.type_state.sound_players[i].next.loops_remaining = 0
            self.type_state.sound_players[i].next.current_loop = 0
            self.type_state.sound_players[i].next.volume = 0
            self.type_state.sound_players[i].next.sample_pos = 0
            self.type_state.sound_players[i].next.loop_start_pos = 0
            self.type_state.sound_players[i].next.loop_end_pos = 0
            self.type_state.sound_players[i].next.sound_id = 0
            self.type_state.sound_players[i].next.sound_instance_id = 0
            self.type_state.sound_players[i].next.sound_priority = 0
            self.type_state.sound_players[i].next.fading_status = fading_status_not_fading
            self.type_state.sound_players[i].next.about_to_finish_marker = no_marker
            self.type_state.sound_players[i].next.sound_has_ducking = False
            self.type_state.sound_players[i].next.ducking_stage = ducking_stage_idle
            self.type_state.sound_players[i].next.ducking_control_points = g_array_sized_new(False, False, sizeof(guint8), CONTROL_POINTS_PER_BUFFER)
            self.type_state.sound_players[i].next.marker_count = 0
            self.type_state.sound_players[i].next.markers = g_array_new(False, False, sizeof(guint))

        self.log.debug("Created Track %d %s with the following settings: "
                       "simultaneous_sounds = %d, volume = %f",
                       self.number, self.name, self.max_simultaneous_sounds, self.volume)

        SDL_UnlockAudio()

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudio()

        # Free the specific track type state and other allocated memory
        if self.type_state != NULL:
            for i in range(self.type_state.sound_player_count):
                g_array_free(self.type_state.sound_players[i].current.ducking_control_points, True)
                g_array_free(self.type_state.sound_players[i].next.ducking_control_points, True)
                g_array_free(self.type_state.sound_players[i].current.markers, True)
                g_array_free(self.type_state.sound_players[i].next.markers, True)

            PyMem_Free(self.type_state.sound_players)
            PyMem_Free(self.type_state)
            self.type_state = NULL
            if self.state != NULL:
                self.state.type_state = NULL

        SDL_UnlockAudio()

    def __repr__(self):
        return '<Track.{}.Standard.{}>'.format(self.number, self.name)

    @property
    def type(self):
        return "standard"

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track accepts in-memory sounds"""
        return True

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track accepts streaming sounds"""
        return True

    @property
    def max_simultaneous_sounds(self):
        """Return the number of sounds that can be played simultaneously on this track"""
        return self._max_simultaneous_sounds

    cdef int _get_idle_sound_player(self):
        """
        Returns the index of the first idle sound player on the track.  If all
        players are currently busy playing, -1 is returned.
        """
        SDL_LockAudio()

        for index in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[index].status == player_idle:
                SDL_UnlockAudio()
                return index

        SDL_UnlockAudio()
        return -1

    def process(self):
        """Processes the track queue each tick."""

        cdef bint keep_checking = True
        cdef int idle_sound_player
        cdef GSList *iterator = NULL

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockAudio()

        while keep_checking:
            # See if there are now any idle sound players
            idle_sound_player = self._get_idle_sound_player()
            if idle_sound_player >= 0:
                # Found an idle player, check if there are any sounds queued for playback
                sound_instance = self._get_next_sound()

                if sound_instance is not None:
                    self.log.debug("Getting sound from queue %s", sound_instance)
                    self._play_sound_on_sound_player(sound_instance=sound_instance, player=idle_sound_player)
                else:
                    keep_checking = False
            else:
                keep_checking = False

        # Process track notification messages
        if self.state.notification_messages != NULL:
            self.state.notification_messages = g_slist_reverse(self.state.notification_messages)
            iterator = self.state.notification_messages
            while iterator != NULL:
                self.process_notification_message(<NotificationMessageContainer*>iterator.data)
                g_slice_free1(sizeof(NotificationMessageContainer), iterator.data)
                iterator = iterator.next

            g_slist_free(self.state.notification_messages)
            self.state.notification_messages = NULL

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockAudio()

    cdef process_notification_message(self, NotificationMessageContainer *notification_message):
        """Process a notification message to this track"""

        if notification_message == NULL:
            return

        SDL_LockAudio()

        # Check for track notification messages first (they do not need sound instance information)
        if notification_message.message in (notification_track_stopped, notification_track_paused):
            if notification_message.message == notification_track_stopped:
                self._reset_state()
                # Trigger any events
                if self.events_when_stopped is not None:
                    for event in self.events_when_stopped:
                        self.mc.post_mc_native_event(event, track=self._name)

            elif notification_message.message == notification_track_paused:
                # Trigger any events
                if self.events_when_paused is not None:
                    for event in self.events_when_paused:
                        self.mc.post_mc_native_event(event, track=self._name)
                pass

            SDL_UnlockAudio()
            return

        self.log.debug("Processing notification message %d for sound instance (id: %d)",
                       notification_message.message, notification_message.sound_instance_id)

        if notification_message.sound_instance_id not in self._playing_instances_by_id:
            self.log.warning("Received a notification message for a sound instance (id: %d) "
                             "that is no longer managed in the audio library. "
                             "Notification will be discarded.",
                             notification_message.sound_instance_id)

        elif notification_message.message == notification_sound_started:
            sound_instance = self._playing_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_playing()

        elif notification_message.message == notification_sound_stopped:
            sound_instance = self._playing_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_stopped()
                self.log.debug("Removing sound instance %s from playing sound "
                               "instance dictionary", str(sound_instance))
                del self._playing_instances_by_id[sound_instance.id]

        elif notification_message.message == notification_sound_looping:
            sound_instance = self._playing_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_looping()

        elif notification_message.message == notification_sound_about_to_finish:
            sound_instance = self._playing_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_about_to_finish()

        elif notification_message.message == notification_sound_marker:
            sound_instance = self._playing_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_marker(notification_message.data.marker.id)
        else:
            raise AudioException("Unknown notification message received on %s track", self.name)

        SDL_UnlockAudio()

    def _get_next_sound(self):
        """
        Returns the next sound in the priority queue ready for playback.

        Returns: A SoundInstance object. If the queue is empty, None is returned.

        This method ensures that the sound that is returned has not expired.
        If the next sound in the queue has expired, it is discarded and the
        next sound that has not expired is returned.
        """
        # We don't want to go through the entire sound queue more than once
        # in this method so keep track of the entry ids of the items we've
        # processed.  Once an item has been processed and retrieved again,
        # we are done and return None.
        cdef list sound_instances_retrieved_from_queue = list()
        while True:
            # Return none if sound queue is empty
            if len(self._sound_queue) == 0:
                return None

            # Get the next item in the queue (sorted by priority and expiration time)
            sound_instance = heappop(self._sound_queue)

            # Check if we've already processed the sound instance during this call (if
            # so, put it back in the queue and return)
            if sound_instance in sound_instances_retrieved_from_queue:
                heappush(self._sound_queue, sound_instance)
                return None

            # Keep track of entries we've processed during this call
            sound_instances_retrieved_from_queue.append(sound_instance)

            # If the sound is still loading and not expired, put it back in the queue
            if not sound_instance.sound.loaded and sound_instance.sound.loading and \
                    (sound_instance.exp_time is None or sound_instance.exp_time > time.time()):
                heappush(self._sound_queue, sound_instance)
                self.log.debug("Next pending sound in queue is still loading, "
                               "re-queueing sound %s",
                               sound_instance)
            else:
                # Return the next sound from the priority queue if it has not expired
                if sound_instance.exp_time is None or sound_instance.exp_time > time.time():
                    self.log.debug("Retrieving next pending sound from queue %s", sound_instance)
                    sound_instance.set_pending()  # Notify sound instance it is no longer queued
                    return sound_instance
                else:
                    self.log.debug("Discarding expired sound from queue %s", sound_instance)
                    sound_instance.set_expired()  # Notify sound instance it has expired

    def _remove_sound_from_queue(self, sound not None):
        """
        Removes all sound instances of the specify sound from the priority sound queue.

        Args:
            sound: The sound object to remove
        """
        cdef list sound_queue_copy = self._sound_queue.copy()
        for sound_instance in sound_queue_copy:
            if sound_instance.sound_id == sound.id:
                self._sound_queue.remove(sound_instance)
                sound_instance.set_canceled()

        heapify(self._sound_queue)

    def _remove_sound_instance_from_queue(self, sound_instance not None):
        """
        Removes a sound from the priority sound queue.
        Args:
            sound_instance: The sound instance object to remove
        """
        try:
            self._sound_queue.remove(sound_instance)
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()
            heapify(self._sound_queue)
        except ValueError:
            pass

    def _remove_all_sounds_with_context_from_queue(self, context):
        """Removes all sounds with the specified context from the priority sound queue.
        """
        for sound_instance in self._sound_queue.copy():
            if sound_instance.context == context:
                self.log.debug("Removing pending sound with context %s from queue %s", context, sound_instance)
                sound_instance.set_canceled()
                self._sound_queue.remove(sound_instance)

        heapify(self._sound_queue)

    def _remove_all_sounds_with_key_from_queue(self, key):
        """Removes all sounds with the specified key from the priority sound queue.
        """
        for sound_instance in self._sound_queue.copy():
            if sound_instance.key == key:
                self.log.debug("Removing pending sound with key %s from queue %s", key, sound_instance)
                sound_instance.set_canceled()
                self._sound_queue.remove(sound_instance)

        heapify(self._sound_queue)

    def _remove_all_sounds_from_queue(self):
        """Removes all sounds from the priority sound queue.
        """
        for sound_instance in self._sound_queue:
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()

        self._sound_queue.clear()

    cdef int _get_playing_sound_count(self, Uint64 sound_id):
        """Return the number of currently playing instances of the given sound id"""
        cdef int count = 0
        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_id == sound_id:
                count += 1

        SDL_UnlockAudio()
        return count

    cdef list _get_playing_sound_instances(self, Uint64 sound_id):
        """Return the list of currently playing instances of the given sound id"""
        cdef list instances = list()
        cdef Uint64 instance_id

        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_id == sound_id:

                if self.type_state.sound_players[i].status == player_replacing:
                    instance_id = self.type_state.sound_players[i].next.sound_instance_id
                else:
                    instance_id = self.type_state.sound_players[i].current.sound_instance_id

                if instance_id in self._playing_instances_by_id:
                    instances.append(self._playing_instances_by_id[instance_id])

        SDL_UnlockAudio()
        return instances

    def _get_oldest_playing_sound_instance(self, Uint64 sound_id):
        """Return the oldest sound instance currently playing"""
        cdef list playing_instances = self._get_playing_sound_instances(sound_id)

        if not playing_instances:
            return None

        oldest_instance = playing_instances[0]
        for sound_instance in playing_instances[1:]:
            if sound_instance.timestamp < oldest_instance.timestamp:
                oldest_instance = sound_instance

        return oldest_instance

    def _get_newest_playing_sound_instance(self, Uint64 sound_id):
        """Return the newest sound instance currently playing"""
        cdef list playing_instances = self._get_playing_sound_instances(sound_id)

        if not playing_instances:
            return None

        newest_instance = playing_instances[0]
        for sound_instance in playing_instances[1:]:
            if sound_instance.timestamp > newest_instance.timestamp:
                newest_instance = sound_instance

        return newest_instance

    def play_sound(self, sound not None, context=None, settings=None):
        """
        Plays a sound on the current track.
        Args:
            sound: The SoundAsset or SoundPool object to play
            context: The context from which the sound is played.
            settings: A dictionary of settings for playback
        Returns:
            A SoundInstance object if the sound will be played (or queued for playback).
            None if the sound could not be played.
        """
        self.log.debug("play_sound - Processing sound '%s' for playback.", sound.name)

        SDL_LockAudio()

        # A try/else/finally block is used here to ensure SDL_UnlockAudio is always called
        # before the function returns (since there are so many return branches it is easier
        # to use than placing the SDL_UnlockAudio call before every return).
        try:

            # Sound cannot be played if the track is stopped or paused
            if self.state.status == track_status_stopped or self.state.status == track_status_paused:
                self.log.debug("play_sound - %s track is not currently playing and "
                               "therefore the request to play sound %s will be canceled",
                               self.name, sound.name)
                return None

            sound_instance = None

            # Check if sound can be played based on if the maximum number of playing instances of
            # this sound has been reached or not.
            if sound.simultaneous_limit is not None and self._get_playing_sound_count(sound.id) >= sound.simultaneous_limit:

                # Maximum number of simultaneous instances of the specified sound has been reached.
                # Perform action based on sound stealing method
                if sound.stealing_method == SoundStealingMethod.oldest:
                    oldest_instance = self._get_oldest_playing_sound_instance(sound.id)
                    if oldest_instance is not None:
                        sound_instance = SoundInstance(sound, context, settings)
                        self._replace_sound_instance(oldest_instance, sound_instance)
                        self.log.debug("Sound %s has reached the maximum number of instances. "
                                       "Replacing oldest instance", sound.name)
                        return sound_instance

                elif sound.stealing_method == SoundStealingMethod.newest:
                    newest_instance = self._get_newest_playing_sound_instance(sound.id)
                    if newest_instance is not None:
                        sound_instance = SoundInstance(sound, context, settings)
                        self._replace_sound_instance(newest_instance, sound_instance)
                        self.log.debug("Sound %s has reached the maximum number of instances. "
                                       "Replacing newest instance", sound.name)
                        return sound_instance

                else:
                    # New instance will not be played; it will be skipped
                    self.log.debug("Sound %s has reached the maximum number of instances. "
                                   "Sound will be skipped", sound.name)
                    return None
            else:
                sound_instance = SoundInstance(sound, context, settings)

            if sound_instance.max_queue_time is None:
                sound_instance.exp_time = None
            else:
                sound_instance.exp_time = time.time() + sound_instance.max_queue_time

            # Make sure sound is loaded.  If not, we assume the sound is being loaded and we
            # add it to the queue so it will be picked up on the next loop.
            if not sound_instance.sound.loaded:
                # If the sound is not already loading, load it now
                if not sound_instance.sound.loading:
                    sound_instance.sound.load()

                if sound_instance.max_queue_time != 0:
                    self._queue_sound(sound_instance)
                    self.log.debug("play_sound - Sound %s was not loaded and therefore has been "
                                   "queued for playback.", sound_instance.name)
                else:
                    self.log.debug("play_sound - Sound %s was not loaded and max_queue_time = 0, "
                                   "therefore it has been discarded and will not be played.", sound_instance.name)
                    sound_instance.set_expired()
                    return None

            else:
                # The sound is loaded and ready for playback.
                # If the sound can be played right away (available player) then play it.
                # Is there an available sound player?
                sound_player = self._get_sound_player_with_lowest_priority()
                player = sound_player[0]
                lowest_priority = sound_player[1]

                if lowest_priority is None:
                    self.log.debug("play_sound - Sound player %d is available "
                                   "for playback", player)
                    # Play the sound using the available player
                    self._play_sound_on_sound_player(sound_instance=sound_instance, player=player)
                else:
                    # All sound players are currently busy:
                    self.log.debug("play_sound - No idle sound player is available.")
                    self.log.debug("play_sound - Sound player %d is currently playing the sound with "
                                   "the lowest priority (%d).", player, lowest_priority)

                    # If the lowest priority of all the sounds currently playing is lower than
                    # the requested sound, kill the lowest priority sound and replace it.
                    if sound_instance.priority > lowest_priority:
                        self.log.debug("play_sound - Sound priority (%d) is higher than the "
                                       "lowest sound currently playing (%d). Forcing playback "
                                       "on sound player %d.", sound_instance.priority, lowest_priority, player)
                        self._play_sound_on_sound_player(sound_instance=sound_instance,
                                                         player=player,
                                                         force=True)

                    elif sound_instance.max_queue_time == 0:
                        # The sound could not be played immediately and has now expired (max_queue_time == 0)
                        self.log.debug("play_sound - Sound priority (%d) is less than or equal to the "
                                       "lowest sound currently playing (%d). Sound could not be played"
                                       "immediately and has now expired (max_queue_time = 0) and will "
                                       "not be played.",
                                       sound_instance.priority, lowest_priority)
                        sound_instance.set_expired()
                        return None

                    else:
                        # Add the requested sound to the priority queue
                        self.log.debug("play_sound - Sound priority (%d) is less than or equal to the "
                                       "lowest sound currently playing (%d). Sound will be queued "
                                       "for playback.", sound_instance.priority, lowest_priority)
                        self._queue_sound(sound_instance)

        except Exception as ex:
            # An exception occurred, sound could not be played
            self.log.error("Track %s: play_sound encountered an unexpected exception while "
                           "attempting to play the %s sound: %s", self.name, sound.name, ex)
            raise AudioException("Track {} play_sound encountered an unexpected exception while "
                                 "attempting to play the {} sound.".format(self.name, sound.name)) from ex

        else:
            # No exception occurred, return the newly created sound instance that will be played
            return sound_instance

        finally:
            # Always unlock the audio mutex before returning
            SDL_UnlockAudio()

    def _replace_sound_instance(self, old_instance not None, sound_instance not None):
        """
        Replace a currently playing instance with another sound instance.
        Args:
            old_instance: The currently playing sound instance to replace
            sound_instance: The new sound instance to begin playing immediately
        """

        self.log.debug("replace_sound_instance - Preparing to replace existing sound with a new sound instance")

        # Find which player is currently playing the specified sound instance to replace
        SDL_LockAudio()
        player = self._get_player_playing_sound_instance(old_instance)

        if player >= 0:
            self._play_sound_on_sound_player(sound_instance, player, force=True)
        else:
            self.log.debug("replace_sound_instance - Could not locate specified sound instance to replace")
            sound_instance.set_canceled()

        SDL_UnlockAudio()

    def _queue_sound(self, sound_instance not None):
        """Adds a sound to the queue to be played when a sound player becomes available.

        Args:
            sound_instance: The SoundInstance object to play.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """
        heappush(self._sound_queue, sound_instance)

        # Notify sound instance it has been queued
        sound_instance.set_queued()
        self.log.debug("Queueing sound %s", sound_instance)

    def _get_sound_instances_for_sound(self, sound not None):
        """Return list of sound instances of the given sound."""

        cdef list instances = list()

        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_id == sound.id:

                sound_instance_id = self.type_state.sound_players[i].current.sound_instance_id
                if sound_instance_id in self._playing_instances_by_id:
                    instances.append(self._playing_instances_by_id[sound_instance_id])

        SDL_UnlockAudio()

        return instances

    def stop_sound(self, sound not None, fade_out=None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound: The Sound to stop
            fade_out: Optional amount of time (seconds) to fade out before stopping
        """
        for sound_instance in self._get_sound_instances_for_sound(sound):
            self.stop_sound_instance(sound_instance, fade_out)

        self._remove_sound_from_queue(sound)

    def stop_sound_instance(self, sound_instance not None, fade_out=None):
        """
        Stops the specified sound instance immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound_instance: The SoundInstance to stop
            fade_out: Optional amount of time (seconds) to fade out before stopping
        """
        cdef SoundPlayer *player

        SDL_LockAudio()

        self.log.debug("Stopping sound %s and removing any pending instances from queue", sound_instance.name)

        if fade_out is None:
            fade_out = sound_instance.fade_out

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:

                # Update player to stop playing sound
                player = cython.address(self.type_state.sound_players[i])

                # Calculate fade out (if necessary)
                player.current.fade_steps_remaining = fade_out * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
                if player.current.fade_steps_remaining > 0:
                    player.current.fade_out_steps = player.current.fade_steps_remaining
                    player.current.fading_status = fading_status_fading_out
                    player.status = player_stopping
                else:
                    # Sound will stop immediately - send sound stopped notification
                    send_sound_stopped_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)
                    player.status = player_idle

                # Adjust ducking release (if necessary)
                if player.current.sound_has_ducking:
                    # player.current.ducking_settings.release_duration = min(sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor, request_message.data.stop.fade_out_duration)
                    # player.current.ducking_settings.release_start_pos = player.current.sample_pos
                    # TODO: Add more intelligent ducking release point calculation here:
                    #       Take into consideration whether ducking is already in progress and when it was
                    #       originally scheduled to finish.
                    pass

        # Remove any instances of the specified sound that are pending in the sound queue
        self._remove_sound_instance_from_queue(sound_instance)

        SDL_UnlockAudio()

    def stop_sound_looping(self, sound not None):
        """
        Cancels looping for all instances of the specified sound on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound: The Sound to stop looping
        """
        for sound_instance in self._get_sound_instances_for_sound(sound):
            self.stop_sound_instance_looping(sound_instance)

        self._remove_sound_from_queue(sound)

    def stop_sound_instance_looping(self, sound_instance not None):
        """
        Stops the specified sound instance on the track after the current loop iteration
        has finished. Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """

        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:
                # Set sound's loops_remaining variable to zero and loop end position to the end of the sound
                self.type_state.sound_players[i].current.loops_remaining = 0
                self.type_state.sound_players[i].current.loop_end_pos = self.type_state.sound_players[
                    i].current.sample.data.memory.size

        # Remove any instances of the specified sound that are pending in the sound queue.
        if self.sound_instance_is_in_queue(sound_instance):
            self._remove_sound_instance_from_queue(sound_instance)

        SDL_UnlockAudio()

    def clear_context(self, context):
        """
        Triggers the end mode action for current sound instances played from the specified context.
        Any queued instances with a matching context will be canceled (removed).

        Args:
            context: The context to clear
        """
        # If this track is managed by a playlist controller, do not clear the context as that
        # will be handled by the playlist controller.
        if self.mc.sound_system.audio_interface.get_playlist_controller(self._name):
            self.log.debug("Skip clearing context %s (playlist controller will handle it)", context)
            return

        self.log.debug("Clearing context %s", context)

        SDL_LockAudio()

        # Clear any instances in the queue with the given context value
        self._remove_all_sounds_with_context_from_queue(context)

        for sound_instance in list(self._playing_instances_by_id.values()):
            if sound_instance.context == context:
                # Stop or stop looping the sound instance (depends upon mode end action value)
                if sound_instance.stop_on_mode_end:
                    self.stop_sound_instance(sound_instance)
                else:
                    self.stop_sound_instance_looping(sound_instance)

        SDL_UnlockAudio()

    def _reset_state(self):
        """Resets the track state (stops all sounds immediately and clears the queue)"""
        SDL_LockAudio()

        self.log.debug("Resetting track state (sounds will be stopped and queue cleared")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                # Set stop sound event
                send_sound_stopped_notification(i,
                                                self.type_state.sound_players[i].current.sound_id,
                                                self.type_state.sound_players[i].current.sound_instance_id,
                                                self.state)
                self.type_state.sound_players[i].status = player_idle

        # Remove all sounds that are pending in the sound queue.
        self._remove_all_sounds_from_queue()

        SDL_UnlockAudio()

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        SDL_LockAudio()

        self.log.debug("Stopping all sounds and removing any pending sounds from queue")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:

                # Update player to stop playing sound
                player = cython.address(self.type_state.sound_players[i])

                # Calculate fade out (if necessary)
                player.current.fade_steps_remaining = <Uint32>(fade_out_seconds * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point)
                if player.current.fade_steps_remaining > 0:
                    player.current.fade_out_steps = player.current.fade_steps_remaining
                    player.current.fading_status = fading_status_fading_out
                    player.status = player_stopping
                else:
                    # Sound will stop immediately - send sound stopped notification
                    send_sound_stopped_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)
                    player.status = player_idle

                # Adjust ducking release (if necessary)
                if player.current.sound_has_ducking:
                    # player.current.ducking_settings.release_duration = min(sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor, request_message.data.stop.fade_out_duration)
                    # player.current.ducking_settings.release_start_pos = player.current.sample_pos
                    # TODO: Add more intelligent ducking release point calculation here:
                    #       Take into consideration whether ducking is already in progress and when it was
                    #       originally scheduled to finish.
                    pass

        # Remove all sounds that are pending in the sound queue.
        self._remove_all_sounds_from_queue()

        SDL_UnlockAudio()

    cdef tuple _get_sound_player_with_lowest_priority(self):
        """
        Retrieves the sound player currently with the lowest priority.

        Returns:
            A tuple consisting of the sound player index and the priority of
            the sound playing on that player (or None if the player is idle).

        """
        SDL_LockAudio()

        cdef int lowest_priority = 2147483647
        cdef int sound_player = -1
        cdef int i

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status == player_idle:
                SDL_UnlockAudio()
                return i, None
            elif self.type_state.sound_players[i].current.sound_priority < lowest_priority:
                lowest_priority = self.type_state.sound_players[i].current.sound_priority
                sound_player = i

        SDL_UnlockAudio()
        return sound_player, lowest_priority

    cdef bint _play_sound_on_sound_player(self, sound_instance, int player, bint force=False):
        """
        Plays a sound using the specified sound player

        Args:
            sound_instance: The SoundInstance object to play
            player: The player number to use to play the sound
            force: Flag indicating whether or not the sound should be forced to play if
                the player is already busy playing another sound.

        Returns:
            True if sound instance was able to be played, False otherwise
        """
        self.log.debug("_play_sound_on_sound_player: %s, %s, %s", str(sound_instance), str(player), str(force))

        SDL_LockAudio()

        # The sound cannot be played if the track is stopped or paused
        if self.state.status == track_status_stopped or self.state.status == track_status_paused:
            self.log.debug("_play_sound_on_sound_player - %s track is not currently playing and "
                           "therefore the request to play sound %s will be canceled",
                           self.name, sound_instance.name)
            sound_instance.set_canceled()
            SDL_UnlockAudio()
            return False

        if not sound_instance.sound.loaded:
            self.log.debug("Specified sound is not loaded, could not "
                           "play sound %s", sound_instance.name)
            SDL_UnlockAudio()
            return False

        # Make sure the player in range
        if player in range(self.type_state.sound_player_count):

            # If the specified sound player is not idle do not play the sound if force is not set
            if self.type_state.sound_players[player].status != player_idle and not force:
                self.log.debug("All sound players are currently in use, "
                               "could not play sound %s", sound_instance.name)
                SDL_UnlockAudio()
                return False

            # Add sound to the dictionary of active sound instances
            self.log.debug("Adding sound instance %s to active sound dictionary", str(sound_instance))
            self._playing_instances_by_id[sound_instance.id] = sound_instance

            # Check if sound player is idle
            if self.type_state.sound_players[player].status == player_idle:
                # Start the player playing the sound instance
                self._set_player_playing(cython.address(self.type_state.sound_players[player]), sound_instance)
            else:
                # The player is currently busy playing another sound, force it to be replaced with the sound instance
                self._set_player_replacing(cython.address(self.type_state.sound_players[player]), sound_instance)

            self.log.debug("Sound %s is set to begin playback on standard track (loops=%d)",
                           sound_instance.name, sound_instance.loops)

            SDL_UnlockAudio()
            return True

        SDL_UnlockAudio()
        return False

    cdef _set_player_sound_settings(self, SoundSettings *sound_settings, object sound_instance):
        """
        Set sound settings for the player from the sound instance.
        Args:
            sound_settings: A pointer to a SoundSettings structure
            sound_instance: The sound instance
        """
        cdef int bytes_per_sample_frame

        if sound_settings == NULL or sound_instance is None:
            return

        # Get the sound sample buffer container
        cdef SoundFile sound_container = sound_instance.container

        # Setup the player to start playing the sound
        sound_settings.sample_pos = <Uint32>(sound_instance.start_at * self.state.callback_data.seconds_to_bytes_factor)
        sound_settings.sample_pos = self._fix_sample_frame_pos(sound_settings.sample_pos, self.state.callback_data.bytes_per_sample, self.state.callback_data.channels)
        if sound_settings.sample_pos > sound_container.sample.size:
            sound_settings.sample_pos = 0

        # Setup loop start position (defaults to 0)
        sound_settings.loop_start_pos = <Uint32>(sound_instance.loop_start_at * self.state.callback_data.seconds_to_bytes_factor)
        sound_settings.loop_start_pos = self._fix_sample_frame_pos(sound_settings.loop_start_pos, self.state.callback_data.bytes_per_sample, self.state.callback_data.channels)
        if sound_settings.loop_start_pos > sound_container.sample.size:
            sound_settings.loop_start_pos = 0

        # Setup loop end position (if loop_end_at is None, set loop end to end of sound)
        if sound_instance.loop_end_at is None:
            sound_settings.loop_end_pos = sound_container.sample.size
        else:
            sound_settings.loop_end_pos = <Uint32>(sound_instance.loop_end_at * self.state.callback_data.seconds_to_bytes_factor)
            sound_settings.loop_end_pos = self._fix_sample_frame_pos(sound_settings.loop_end_pos, self.state.callback_data.bytes_per_sample, self.state.callback_data.channels)
            if sound_settings.loop_end_pos > sound_container.sample.size:
                sound_settings.loop_end_pos = sound_container.sample.size

        sound_settings.current_loop = 0
        sound_settings.sound_id = sound_instance.sound_id
        sound_settings.sound_instance_id = sound_instance.id
        sound_settings.sample = cython.address(sound_container.sample)
        sound_settings.volume = <Uint8>(sound_instance.volume * SDL_MIX_MAXVOLUME)
        sound_settings.volume_left = sound_settings.volume
        sound_settings.volume_right = sound_settings.volume
        sound_settings.loops_remaining = sound_instance.loops
        sound_settings.sound_priority = sound_instance.priority

        # If the sound is not set to loop, adjust the loop end position to the end of the sound
        if sound_settings.loops_remaining == 0:
            sound_settings.loop_end_pos = sound_container.sample.size

        # Apply simple linear pan/balance setting
        if self.state.callback_data.channels == 2:
            if sound_instance.pan < 0:
                sound_settings.volume_left = sound_settings.volume
                sound_settings.volume_right = <Uint8>(sound_instance.volume * SDL_MIX_MAXVOLUME * in_out_quad(sound_instance.pan + 1.0))
            else:
                sound_settings.volume_left = <Uint8>(sound_instance.volume * SDL_MIX_MAXVOLUME * in_out_quad(1.0 - sound_instance.pan))
                sound_settings.volume_right = sound_settings.volume

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        sound_settings.fade_in_steps = sound_instance.fade_in * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        sound_settings.fade_out_steps = sound_instance.fade_out * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        sound_settings.fade_steps_remaining = sound_settings.fade_in_steps
        if sound_settings.fade_steps_remaining > 0:
            sound_settings.fading_status = fading_status_fading_in
        else:
            sound_settings.fading_status = fading_status_not_fading

        # Markers
        sound_settings.marker_count = sound_instance.marker_count
        g_array_set_size(sound_settings.markers, sound_settings.marker_count)
        for index in range(sound_instance.marker_count):
            g_array_insert_val_uint(sound_settings.markers,
                                    index,
                                    <guint>(sound_instance.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor))

        # Set almost finished marker (calculate based on the end of the sound)
        if sound_instance.about_to_finish_time is None:
            sound_settings.about_to_finish_marker = no_marker
        elif sound_instance.about_to_finish_time > sound_container.duration:
            sound_settings.about_to_finish_marker = 0
        else:
            sound_settings.about_to_finish_marker = (sound_container.duration - sound_instance.about_to_finish_time) * self.state.callback_data.seconds_to_bytes_factor

        # If the sound has ducking settings, apply them
        if sound_instance.ducking is not None and sound_instance.ducking.track_bit_mask != 0:
            # To convert between the number of seconds and a buffer position (bytes), we need to
            # account for the sample rate (samples per second), the number of audio channels, and the
            # number of bytes per sample (all samples are 16 bits)
            sound_settings.sound_has_ducking = True
            sound_settings.ducking_stage = ducking_stage_delay
            sound_settings.ducking_settings.track_bit_mask = sound_instance.ducking.track_bit_mask
            sound_settings.ducking_settings.attack_start_pos = sound_instance.ducking.delay * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attack_duration = sound_instance.ducking.attack * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attenuation_volume = <Uint8>(sound_instance.ducking.attenuation * SDL_MIX_MAXVOLUME)
            sound_settings.ducking_settings.release_duration = sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor

            # Release point is relative to the end of the sound
            sound_settings.ducking_settings.release_start_pos = (sound_container.duration - sound_instance.ducking.release_point) * self.state.callback_data.seconds_to_bytes_factor
        else:
            # Sound does not have ducking, assign settings appropriately
            sound_settings.sound_has_ducking = False
            sound_settings.ducking_stage = ducking_stage_idle
            sound_settings.ducking_settings.track_bit_mask = 0
            sound_settings.ducking_settings.attack_start_pos = 0
            sound_settings.ducking_settings.attack_duration = 0
            sound_settings.ducking_settings.attenuation_volume = SDL_MIX_MAXVOLUME
            sound_settings.ducking_settings.release_duration = 0
            sound_settings.ducking_settings.release_start_pos = 0

        # Special handling is needed to start streaming for the specified sound at the correct location
        if sound_container.sample.type == sound_type_streaming:
            # Seek to the specified start position
            gst_element_seek_simple(sound_container.sample.data.stream.pipeline,
                                    GST_FORMAT_TIME,
                                    <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT),
                                    sound_instance.start_at * GST_SECOND)
            with nogil:
                ret = gst_element_set_state(sound_container.sample.data.stream.pipeline, GST_STATE_PLAYING)

    cdef _set_player_playing(self, SoundPlayer *player, object sound_instance):
        """
        Sets the player status and sound settings to begin playing the sound instance
        Args:
            player: A pointer to the SoundPlayer on which to play the sound
            sound_instance: The sound instance to begin playing
        """
        if player == NULL or sound_instance is None:
            return

        # Setup the player to start playing the sound
        player.status = player_playing
        self._set_player_sound_settings(cython.address(player.current), sound_instance)

        # Send sound started notification
        send_sound_started_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)

        self.log.debug("Sound %s is set to begin playback on playlist track (loops=%d)",
                       sound_instance.name, sound_instance.loops)

    cdef _set_player_replacing(self, SoundPlayer *player, object sound_instance):
        """
        Sets the player status and sound settings to replace the currently playing sound with the
        sound instance.
        Args:
            player: A pointer to the SoundPlayer on which to replace the sound
            sound_instance: The sound instance to begin playing
        """
        if player == NULL or sound_instance is None:
            return

        # Set current sound to fade out quickly
        player.current.fade_out_steps = self.state.callback_data.quick_fade_steps
        player.current.fade_steps_remaining = self.state.callback_data.quick_fade_steps
        player.current.fading_status = fading_status_fading_out

        # Set the next sound to play immediately after the current one fades out
        player.status = player_replacing
        self._set_player_sound_settings(cython.address(player.next), sound_instance)

        # TODO: Figure out how to handle ducking when replacing an existing sound

    cdef int _get_player_playing_sound_instance(self, sound_instance):
        """
        Return the player currently playing the specified sound instance
        Args:
            sound_instance: The SoundInstance to find

        Returns:
            The sound player number currently playing the specified sound instance or -1 if the
            sound instance is not currently playing.
        """
        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockAudio()
                return i

        SDL_UnlockAudio()
        return -1

    cdef Uint32 _fix_sample_frame_pos(self, Uint32 sample_pos, Uint8 bytes_per_sample, int channels):
        """
        Rounds up sample position to a sample frame boundary (audio distortion may occur if starting
        in the middle of a sample frame).

        Args:
            sample_pos: The sample position
            bytes_per_sample: The number of bytes per sample 
            channels: The number of audio channels

        Returns:
            sample_pos rounded to the nearest sample frame boundary
        """
        cdef int bytes_per_sample_frame = bytes_per_sample * channels
        return bytes_per_sample_frame * ceil(sample_pos / bytes_per_sample_frame)

    def get_playing_sound_instance_by_id(self, sound_instance_id):
        if sound_instance_id in self._playing_instances_by_id:
            return self._playing_instances_by_id[sound_instance_id]
        else:
            return None

    def get_status(self):
        """
        Get the current track status (status of all sound players on the track).
        Used for debugging and testing.
        Returns:
            A list of status dictionaries containing the current settings for each
            sound player.
        """
        SDL_LockAudio()
        status = []
        for player in range(self.type_state.sound_player_count):
            status.append({
                "player": player,
                "status": TrackStandard.player_status_to_text(<int>self.type_state.sound_players[player].status),
                "fading_status": TrackStandard.player_fading_status_to_text(<int>self.type_state.sound_players[player].current.fading_status),
                "volume": self.type_state.sound_players[player].current.volume,
                "sound_id": self.type_state.sound_players[player].current.sound_id,
                "sound_instance_id": self.type_state.sound_players[player].current.sound_instance_id,
                "priority": self.type_state.sound_players[player].current.sound_priority,
                "loops": self.type_state.sound_players[player].current.loops_remaining,
                "current_loop": self.type_state.sound_players[player].current.current_loop,
                "has_ducking": self.type_state.sound_players[player].current.sound_has_ducking,
                "sample_pos": self.type_state.sound_players[player].current.sample_pos,
                "loop_start_pos": self.type_state.sound_players[player].current.loop_start_pos,
                "loop_end_pos": self.type_state.sound_players[player].current.loop_end_pos
            })

            self.log.debug("Status - Player %d: Status=%s, Sound=%d, SoundInstance=%d"
                           "Priority=%d, Loops=%d, SamplePos=%d",
                           player,
                           TrackStandard.player_status_to_text(
                               self.type_state.sound_players[player].status),
                           self.type_state.sound_players[player].current.sound_id,
                           self.type_state.sound_players[player].current.sound_instance_id,
                           self.type_state.sound_players[player].current.sound_priority,
                           self.type_state.sound_players[player].current.loops_remaining,
                           self.type_state.sound_players[player].current.sample_pos)

        SDL_UnlockAudio()

        return status

    def get_sound_queue_count(self):
        """
        Gets the number of sounds currently in the track sound queue.
        Returns:
            Integer number of sounds currently in the track sound queue.
        """
        return len(self._sound_queue)

    def get_sound_players_in_use_count(self):
        """
        Gets the current count of sound players in use on the track.  Used for
        debugging and testing.
        Returns:
            Integer number of sound players currently in use on the track.
        """
        players_in_use_count = 0
        SDL_LockAudio()
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                players_in_use_count += 1
        SDL_UnlockAudio()
        return players_in_use_count

    def sound_is_playing(self, sound not None):
        """Returns whether or not the specified sound is currently playing on the track"""
        SDL_LockAudio()
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_id == sound.id:
                SDL_UnlockAudio()
                return True

        SDL_UnlockAudio()
        return False

    def sound_instance_is_playing(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently playing on the track"""
        SDL_LockAudio()
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockAudio()
                return True

        SDL_UnlockAudio()
        return False

    def sound_is_in_queue(self, sound not None):
        """Returns whether or not an instance of the specified sound is currently in the queue"""
        for sound_instance in self._sound_queue:
            if sound_instance.sound.id == sound.id:
                return True

        return False

    def sound_instance_is_in_queue(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently in the queue"""
        return sound_instance in self._sound_queue

    @staticmethod
    def player_status_to_text(int status):
        """
        Converts a sound player status value into an equivalent text string.  Used for testing
        purposes only.
        Args:
            status: Integer sound player status value

        Returns:
            string containing the equivalent status text
        """
        status_values = {
            player_idle: "idle",
            player_pending: "pending",
            player_replacing: "replacing",
            player_playing: "playing",
            player_finished: "finished",
            player_stopping: "stopping",
        }

        try:
            return status_values.get(status)
        except KeyError:
            return "unknown"

    @staticmethod
    def player_fading_status_to_text(int fading_status):
        """
        Converts a sound player fading status value into an equivalent text string.  Used for
        testing purposes only.
        Args:
            fading_status: Integer sound player fading status value

        Returns:
            string containing the equivalent fading status text
        """
        fading_status_values = {
            fading_status_not_fading: "not fading",
            fading_status_fading_in: "fade in",
            fading_status_fading_out: "fade out",
        }

        try:
            return fading_status_values.get(fading_status)
        except KeyError:
            return "unknown"


# ---------------------------------------------------------------------------
#    Global C functions designed to be called from the static audio callback
#    function (these functions do not use the GIL).
#
#    Note: Because these functions are only called from the audio callback
#    function, we do not need to lock and unlock the mutex in these functions
#    (locking/unlocking of the mutex is already performed in the audio
#    callback function.
# ---------------------------------------------------------------------------

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil:
        """
        Mixes any sounds that are playing on the specified standard track into the specified audio buffer.
        Args:
            track: A pointer to the TrackState data structure for the track
            buffer_length: The length of the output buffer (in bytes)
            callback_data: The audio callback data structure
        Notes:
            Notification messages are generated.
        """
        cdef TrackState *target_track
        cdef TrackStandardState *standard_track
        cdef SoundPlayer *player
        cdef int player_num
        cdef int track_num
        cdef int marker_id
        cdef bint end_of_sound
        cdef bint ducking_is_active

        if track == NULL or track.type_state == NULL:
            return

        standard_track = <TrackStandardState*>track.type_state

        # Setup local variables
        cdef Uint32 buffer_bytes_remaining
        cdef Uint32 current_chunk_bytes
        cdef Uint32 track_buffer_pos
        cdef Uint8 control_point
        cdef float progress

        # Loop over track sound players
        for player_num in range(standard_track.sound_player_count):

            player = cython.address(standard_track.sound_players[player_num])

            # If the player is idle, there is nothing to do so move on to the next player
            if player == NULL or player.status == player_idle:
                continue

            # Set flag indicating there is at least some activity on the track (it is active)
            track.active = True

            end_of_sound = False
            track_buffer_pos = 0
            control_point = 0
            buffer_bytes_remaining = buffer_length

            # Loop over output buffer at control rate
            while buffer_bytes_remaining > 0:

                # Determine the number of bytes to process in the current chunk
                current_chunk_bytes = min(buffer_bytes_remaining, callback_data.bytes_per_control_point)

                # Calculate volume of chunk (handle fading)
                if player.current.fading_status == fading_status_fading_in:
                    volume = <Uint8> (in_out_quad((player.current.fade_in_steps - player.current.fade_steps_remaining) / player.current.fade_in_steps) * player.current.volume)
                    player.current.fade_steps_remaining -= 1
                    if player.current.fade_steps_remaining == 0:
                        player.current.fading_status = fading_status_not_fading
                elif player.current.fading_status == fading_status_fading_out:
                    volume = <Uint8> (in_out_quad(player.current.fade_steps_remaining / player.current.fade_out_steps) * player.current.volume)
                    player.current.fade_steps_remaining -= 1
                else:
                    volume = player.current.volume

                # Copy samples for chunk to output buffer and apply volume
                if player.current.sample.type == sound_type_memory:
                    end_of_sound = get_memory_sound_samples(cython.address(player.current), current_chunk_bytes,
                                                            track.buffer + track_buffer_pos, callback_data.channels,
                                                            volume, track, player_num)
                elif player.current.sample.type == sound_type_streaming:
                    end_of_sound = get_streaming_sound_samples(cython.address(player.current), current_chunk_bytes,
                                                               track.buffer + track_buffer_pos, callback_data.channels,
                                                               volume, track, player_num)

                # Process sound ducking (if applicable)
                if player.current.sound_has_ducking:
                    ducking_is_active = False

                    # Determine control point ducking stage and calculate control point (test stages in reverse order)
                    if player.current.sample_pos >= player.current.ducking_settings.release_start_pos + player.current.ducking_settings.release_duration:
                        # Ducking finished
                        g_array_set_val_uint8(player.current.ducking_control_points, control_point, SDL_MIX_MAXVOLUME)

                    elif player.current.sample_pos >= player.current.ducking_settings.release_start_pos:
                        # Ducking release stage
                        ducking_is_active = True
                        progress = (player.current.sample_pos - player.current.ducking_settings.release_start_pos) / player.current.ducking_settings.release_duration
                        g_array_set_val_uint8(player.current.ducking_control_points,
                                              control_point,
                                              lerpU8(in_out_quad(progress),
                                                     player.current.ducking_settings.attenuation_volume,
                                                     SDL_MIX_MAXVOLUME
                                                     )
                                              )

                    elif player.current.sample_pos >= player.current.ducking_settings.attack_start_pos + player.current.ducking_settings.attack_duration:
                        # Ducking hold state
                        ducking_is_active = True
                        g_array_set_val_uint8(player.current.ducking_control_points, control_point, player.current.ducking_settings.attenuation_volume)

                    elif player.current.sample_pos >= player.current.ducking_settings.attack_start_pos:
                        # Ducking attack stage
                        ducking_is_active = True
                        progress = (player.current.sample_pos - player.current.ducking_settings.attack_start_pos) / player.current.ducking_settings.attack_duration
                        g_array_set_val_uint8(player.current.ducking_control_points,
                                              control_point,
                                              lerpU8(in_out_quad(progress),
                                                     SDL_MIX_MAXVOLUME,
                                                     player.current.ducking_settings.attenuation_volume
                                                     )
                                              )

                    else:
                        # Ducking delay stage
                        g_array_set_val_uint8(player.current.ducking_control_points,
                                              control_point,
                                              SDL_MIX_MAXVOLUME)

                    # Apply ducking to target track(s) (when applicable)
                    if ducking_is_active:
                        for track_num in range(callback_data.track_count):
                            target_track = <TrackState*>callback_data.tracks[track_num]
                            if (1 << track_num) & player.current.ducking_settings.track_bit_mask:
                                target_track.ducking_is_active = True
                                g_array_set_val_uint8(target_track.ducking_control_points,
                                                      control_point,
                                                      min(
                                                          g_array_index_uint8(
                                                              target_track.ducking_control_points,
                                                              control_point),
                                                          g_array_index_uint8(player.current.ducking_control_points,
                                                                              control_point)
                                                      ))

                    # TODO: Hold sound processing until ducking has finished
                    # It is possible to have the ducking release finish after the sound has stopped.  In that
                    # case, silence should be generated until the ducking is done.

                # Process markers (do any markers fall in the current chunk?)
                # Note: the current sample position has already been incremented when the sample data was received so
                # we need to look backwards from the current position to determine if marker falls in chunk window.

                # About to finish marker
                if player.current.about_to_finish_marker != no_marker:
                    if player.current.sample_pos - current_chunk_bytes <= player.current.about_to_finish_marker < player.current.sample_pos:
                        # Marker is in window, send notification
                        send_sound_about_to_finish_notification(player_num,
                                                                player.current.sound_id,
                                                                player.current.sound_instance_id,
                                                                track)
                    # Special check if buffer wraps back around to the beginning of the sample
                    if not end_of_sound and player.current.sample_pos - current_chunk_bytes < 0 and player.current.about_to_finish_marker < player.current.sample_pos:
                        # Marker is in window, send notification
                        send_sound_about_to_finish_notification(player_num,
                                                                player.current.sound_id,
                                                                player.current.sound_instance_id,
                                                                track)

                # User-defined markers
                for marker_id in range(player.current.marker_count):
                    if player.current.sample_pos - current_chunk_bytes <= g_array_index_uint(player.current.markers, marker_id) < player.current.sample_pos:
                        # Marker is in window, send notification
                        send_sound_marker_notification(player_num,
                                                       player.current.sound_id,
                                                       player.current.sound_instance_id,
                                                       track,
                                                       marker_id)
                    # Special check if buffer wraps back around to the beginning of the sample
                    if not end_of_sound and player.current.sample_pos - current_chunk_bytes < 0 and g_array_index_uint(player.current.markers, marker_id) < player.current.sample_pos:
                        # Marker is in window, send notification
                        send_sound_marker_notification(player_num,
                                                       player.current.sound_id,
                                                       player.current.sound_instance_id,
                                                       track,
                                                       marker_id)

                # Check if sound is finished due to a fade out completing
                if player.current.fading_status == fading_status_fading_out and player.current.fade_steps_remaining == 0:
                    end_of_sound = True

                # Sound finished processing
                if end_of_sound:
                    send_sound_stopped_notification(player_num, player.current.sound_id, player.current.sound_instance_id, track)

                    # End of sound behavior depends upon player status
                    if player.status == player_replacing:
                        # Replacing the current sound with a new one: copy sound player settings from next sound to current
                        player.current.sample = player.next.sample
                        player.current.sample_pos = player.next.sample_pos
                        player.current.loop_start_pos = player.next.loop_start_pos
                        player.current.loop_end_pos = player.next.loop_end_pos
                        player.current.current_loop = player.next.current_loop
                        player.current.sound_id = player.next.sound_id
                        player.current.sound_instance_id = player.next.sound_instance_id
                        player.current.volume = player.next.volume
                        player.current.loops_remaining = player.next.loops_remaining
                        player.current.sound_priority = player.next.sound_priority
                        player.current.fade_in_steps = player.next.fade_in_steps
                        player.current.fade_out_steps = player.next.fade_out_steps
                        player.current.fade_steps_remaining = player.next.fade_steps_remaining
                        player.current.fading_status = player.next.fading_status
                        player.current.about_to_finish_marker = player.next.about_to_finish_marker

                        player.current.marker_count = player.next.marker_count
                        g_array_set_size(player.current.markers, player.current.marker_count)
                        for marker_id in range(player.next.marker_count):
                            g_array_insert_val_uint(player.current.markers,
                                                    marker_id,
                                                    g_array_index_uint(player.next.markers, marker_id))

                        if player.next.sound_has_ducking:
                            player.current.sound_has_ducking = True
                            player.current.ducking_stage = ducking_stage_delay
                            player.current.ducking_settings.track_bit_mask = player.next.ducking_settings.track_bit_mask
                            player.current.ducking_settings.attack_start_pos = player.next.ducking_settings.attack_start_pos
                            player.current.ducking_settings.attack_duration = player.next.ducking_settings.attack_duration
                            player.current.ducking_settings.attenuation_volume = player.next.ducking_settings.attenuation_volume
                            player.current.ducking_settings.release_start_pos = player.next.ducking_settings.release_start_pos
                            player.current.ducking_settings.release_duration = player.next.ducking_settings.release_duration
                        else:
                            player.current.sound_has_ducking = False
                            player.current.ducking_stage = ducking_stage_idle
                            player.current.ducking_settings.track_bit_mask = 0
                            player.current.ducking_settings.attack_start_pos = 0
                            player.current.ducking_settings.attack_duration = 0
                            player.current.ducking_settings.attenuation_volume = SDL_MIX_MAXVOLUME
                            player.current.ducking_settings.release_start_pos = 0
                            player.current.ducking_settings.release_duration = 0

                        # Send sound started notification
                        send_sound_started_notification(player_num, player.current.sound_id, player.current.sound_instance_id, track)
                        player.status = player_playing
                        sound_finished = False
                    else:
                        player.status = player_idle
                        break

                # Move to next chunk
                buffer_bytes_remaining -= current_chunk_bytes
                track_buffer_pos += current_chunk_bytes
                control_point += 1

cdef bint get_memory_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, int channels,
                                   Uint8 volume, TrackState *track, int player_num) nogil:
    """
    Retrieves the specified number of bytes from the source sound memory buffer and mixes them into
    the track output buffer at the specified volume.

    Args:
        sound: A pointer to a SoundSettings struct (contains all sound state and settings to play the sound)
        length: The number of samples to retrieve and place in the output buffer
        output_buffer: The output buffer
        channels: The number of channels in the output buffer (1 = mono, 2 = stereo)
        volume: The volume to apply to the output buffer (fixed for the duration of this method)
        track: A pointer to the TrackState struct for the current track
        player_num: The sound player number currently playing the sound (used for notification messages)

    Returns:
        True if sound is finished, False otherwise
    """
    if sound == NULL or output_buffer == NULL:
        return True

    cdef Uint32 samples_remaining_to_output = length
    cdef Uint32 samples_remaining_in_sound
    cdef Uint32 loop_end_pos = sound.loop_end_pos
    cdef Uint32 buffer_pos = 0
    cdef Uint8 *sound_buffer = <Uint8*>sound.sample.data.memory.data
    if sound_buffer == NULL:
        return True

    # Make sure the sound sample position is not starting after the end of the loop position. If so, adjust the
    # end of the loop position to be the end of the sound (keeps the sound player from running past the end of
    # the sound buffer and into other parts of memory creating noise). This should only ever happen if the sound
    # is started after the end of the loop position.
    if sound.sample_pos >= loop_end_pos:
        loop_end_pos = sound.sample.data.memory.size

    # Loop while there are still samples remaining to be output
    while samples_remaining_to_output > 0:

        # Determine how many samples are remaining in the sound buffer before the end of the sound (the
        # current loop position)
        samples_remaining_in_sound = loop_end_pos - sound.sample_pos

        # Determine if we are consuming the entire remaining sound buffer, or just a portion of it
        if samples_remaining_to_output < samples_remaining_in_sound:

            # We are not consuming the entire streaming buffer.  There will still be buffer data remaining for the next call.
            if channels == 2 and False:
                # disabled for now
                Track.mix_audio_stereo(output_buffer + buffer_pos,
                                       <Uint8*>sound.sample.data.memory.data + sound.sample_pos,
                                       samples_remaining_to_output,
                                       sound.volume_left,
                                       sound.volume_right)
            else:
                SDL_MixAudioFormat(output_buffer + buffer_pos, <Uint8*>sound.sample.data.memory.data + sound.sample_pos, track.callback_data.format, samples_remaining_to_output, volume)

            # Update buffer position pointers
            sound.sample_pos += samples_remaining_to_output

            # Sound is not finished, but the output buffer has been filled
            return False
        else:
            # Entire sound buffer consumed. Mix in remaining samples
            if channels == 2 and False:
                # disabled for now
                Track.mix_audio_stereo(output_buffer + buffer_pos,
                                       <Uint8*>sound.sample.data.memory.data + sound.sample_pos,
                                       samples_remaining_to_output,
                                       sound.volume_left,
                                       sound.volume_right)
            else:
                SDL_MixAudioFormat(output_buffer + buffer_pos, <Uint8*>sound.sample.data.memory.data + sound.sample_pos, track.callback_data.format, samples_remaining_in_sound, volume)

            # Update buffer position pointers/samples remaining to place in the output buffer
            samples_remaining_to_output -= samples_remaining_in_sound
            sound.sample_pos += samples_remaining_in_sound
            buffer_pos += samples_remaining_in_sound

        # Check if we are at the end of the source sample buffer (loop if applicable)
        if sound.sample_pos >= loop_end_pos:
            if sound.loops_remaining > 0:
                # At the end and still loops remaining, loop back to the beginning of the loop
                sound.loops_remaining -= 1
                sound.sample_pos = sound.loop_start_pos
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

                # If the sound is on its last loop, set the loop end position to be the end of the sound
                if sound.loops_remaining == 0:
                    sound.loop_end_pos = sound.sample.data.memory.size
                    loop_end_pos = sound.loop_end_pos

            elif sound.loops_remaining == 0:
                # At the end and not looping, the sample has finished playing (return True for end of sound)
                return True

            else:
                # Looping infinitely, loop back to the beginning of the loop
                sound.sample_pos = sound.loop_start_pos
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

    return False

cdef bint get_streaming_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, int channels,
                                      Uint8 volume, TrackState *track, int player_num) nogil:
    """
    Retrieves the specified number of bytes from the source sound streaming buffer and mixes them
    into the track output buffer at the specified volume.

    Args:
        sound: A pointer to a SoundSettings struct (contains all sound state and settings to play the sound)
        length: The number of samples to retrieve and place in the output buffer
        output_buffer: The output buffer
        channels: The number of channels in the output buffer (1 = mono, 2 = stereo)
        volume: The volume to apply to the output buffer (fixed for the duration of this method)
        track: A pointer to the TrackState struct for the current track
        player_num: The sound player number currently playing the sound (used for notification messages)

    Returns:
        True if sound is finished, False otherwise

    Notes:
        The important thing to consider about retrieving samples from the streaming sound source
        is the buffer size used by SDL2 (output) and GStreamer (input) may be very different. A
        buffer is "pulled" synchronously from the streaming source and is held until it is
        completely consumed.  At which point either the sound ends if the source reports is at the
        end of stream (eos), or another buffer is pulled.
    """
    if sound == NULL or output_buffer == NULL or sound.sample.data.stream.pipeline == NULL:
        return True

    cdef Uint32 samples_remaining_to_output = length
    cdef Uint32 samples_remaining_in_map
    cdef Uint32 buffer_pos = 0

    while samples_remaining_to_output > 0:

        # Copy any samples remaining in the streaming buffer
        if sound.sample.data.stream.map_contains_valid_sample_data:
            samples_remaining_in_map = sound.sample.data.stream.map_info.size - sound.sample.data.stream.map_buffer_pos

            # Determine if we are consuming the entire buffer of streaming samples, or just a portion of it
            if samples_remaining_to_output < samples_remaining_in_map:
                # We are not consuming the entire streaming buffer.  There will still be buffer data remaining for the next call.
                if channels == 2 and False:
                    # disabled for now
                    Track.mix_audio_stereo(output_buffer + buffer_pos,
                                           sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                           samples_remaining_to_output,
                                           sound.volume_left,
                                           sound.volume_right)
                else:
                    SDL_MixAudioFormat(output_buffer + buffer_pos,
                                       sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                       track.callback_data.format, samples_remaining_to_output, volume)

                # Update buffer position pointers
                sound.sample.data.stream.map_buffer_pos += samples_remaining_to_output
                sound.sample_pos += samples_remaining_to_output

                # Sound is not finished, but the output buffer has been filled
                return False
            else:
                # Entire buffer of leftover samples consumed.  Free the buffer resources to prepare for next call
                if channels == 2 and False:
                    # disabled for now
                    Track.mix_audio_stereo(output_buffer + buffer_pos,
                                           sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                           samples_remaining_to_output,
                                           sound.volume_left,
                                           sound.volume_right)
                else:
                    SDL_MixAudioFormat(output_buffer + buffer_pos,
                                       sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                       track.callback_data.format, samples_remaining_in_map, volume)

                # Update buffer position pointers/samples remaining to place in the output buffer
                samples_remaining_to_output -= samples_remaining_in_map
                sound.sample_pos += samples_remaining_in_map
                buffer_pos += samples_remaining_in_map

                # Done with the streaming buffer, release references to it
                gst_buffer_unmap(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info)
                gst_sample_unref(sound.sample.data.stream.sample)

                sound.sample.data.stream.buffer = NULL
                sound.sample.data.stream.sample = NULL
                sound.sample.data.stream.map_buffer_pos = 0
                sound.sample.data.stream.map_contains_valid_sample_data = 0

        # Check for eos (end of stream)
        if g_object_get_bool(sound.sample.data.stream.sink, "eos"):

            # At the end of the stream - check if sound should loop or end
            if sound.loops_remaining > 0:
                # At the end and still loops remaining, loop back to the beginning
                sound.loops_remaining -= 1
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

            elif sound.loops_remaining == 0:
                # At the end and not looping, the sample has finished playing (return True for end of sound)
                return True

            else:
                # Looping infinitely, loop back to the beginning
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

            # Seek back to the beginning of the sound's source file
            gst_element_seek_simple(sound.sample.data.stream.pipeline, GST_FORMAT_TIME, <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT), 0)

        # Retrieve the next buffer from the streaming pipeline
        sound.sample.data.stream.sample = c_appsink_pull_sample(sound.sample.data.stream.sink)

        if sound.sample.data.stream.sample == NULL:
            sound.sample.data.stream.null_buffer_count += 1

            # If we've received too many consecutive null buffers, end the sound
            if sound.sample.data.stream.null_buffer_count > CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT:
                return True
        else:
            sound.sample.data.stream.null_buffer_count = 0
            sound.sample.data.stream.buffer = gst_sample_get_buffer(sound.sample.data.stream.sample)

            if gst_buffer_map(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info, GST_MAP_READ):
                sound.sample.data.stream.map_contains_valid_sample_data = 1
                sound.sample.data.stream.map_buffer_pos = 0
            else:
                sound.sample.data.stream.map_contains_valid_sample_data = 0
                sound.sample.data.stream.map_buffer_pos = 0
                gst_sample_unref(sound.sample.data.stream.sample)
                sound.sample.data.stream.sample = NULL

    # The sound has not finished playing, but the output buffer has been filled
    return False
