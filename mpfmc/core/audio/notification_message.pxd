from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport TrackState


# ---------------------------------------------------------------------------
#    Notification Message types
# ---------------------------------------------------------------------------

cdef enum NotificationMessage:
    notification_sound_started = 1            # Notification that a sound has started playing
    notification_sound_stopped = 2            # Notification that a sound has stopped
    notification_sound_looping = 3            # Notification that a sound is looping back to the beginning
    notification_sound_marker = 4             # Notification that a sound marker has been reached during playback
    notification_sound_about_to_finish = 5    # Notification that a sound is about to finish playing
    notification_player_idle = 10             # Notification that a player is now idle and ready to play another sound
    notification_track_stopped = 0            # Notification that the track has stopped
    notification_track_paused = 21            # Notification that the track has been paused
    notification_sound_loop_set_started = 31  # Notification that a sound_loop_set has started playing
    notification_sound_loop_set_stopped = 32  # Notification that a sound_loop_set has stopped
    notification_sound_loop_set_looping = 33  # Notification that a sound_loop_set is looping back to the beginning

ctypedef struct NotificationMessageDataLooping:
    int loop_count
    int loops_remaining

ctypedef struct NotificationMessageDataMarker:
    int id

ctypedef struct NotificationMessageSoundLoopSet:
    long id
    gpointer player


ctypedef union NotificationMessageData:
    NotificationMessageDataLooping looping
    NotificationMessageDataMarker marker
    NotificationMessageSoundLoopSet sound_loop_set

ctypedef struct NotificationMessageContainer:
    NotificationMessage message
    Uint64 sound_id
    Uint64 sound_instance_id
    int player
    NotificationMessageData data


# ---------------------------------------------------------------------------
#    Notification Message functions
# ---------------------------------------------------------------------------

cdef inline NotificationMessageContainer *_create_notification_message() nogil:
    """
    Creates a new notification message.
    :return: A pointer to the new notification message.
    """
    return <NotificationMessageContainer*>g_slice_alloc0(sizeof(NotificationMessageContainer))

cdef inline void send_sound_started_notification(int player, Uint64 sound_id, Uint64 sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound started notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_started
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_stopped_notification(int player, Uint64 sound_id, Uint64 sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound stopped notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_stopped
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_looping_notification(int player, Uint64 sound_id, Uint64 sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound looping notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_looping
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_about_to_finish_notification(int player, Uint64 sound_id, Uint64 sound_instance_id,
                                                         TrackState *track) nogil:
    """
    Sends a sound about to finish notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_about_to_finish
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_marker_notification(int player, Uint64 sound_id, Uint64 sound_instance_id,
                                                TrackState *track,
                                                int marker_id) nogil:
    """
    Sends a sound marker notification message
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
        marker_id: The id of the marker being sent for the specified sound
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_marker
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id
        notification_message.data.marker.id = marker_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_track_stopped_notification(TrackState *track) nogil:
    """
    Sends a track stopped notification
    Args:
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_track_stopped
        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_track_paused_notification(TrackState *track) nogil:
    """
    Sends a track paused notification
    Args:
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_track_paused
        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_loop_set_started_notification(int sound_loop_set_id, Uint64 sound_id, gpointer player, TrackState *track) nogil:
    """
    Sends a sound_loop_set started notification
    Args:
        sound_loop_set_id: The sound_loop_set id
        sound_id: The sound id
        player: A pointer to the sound loop player that was playing this sound loop set 
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_loop_set_started
        notification_message.player = 0
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = 0
        notification_message.data.sound_loop_set.id = sound_loop_set_id
        notification_message.data.sound_loop_set.player = player

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_loop_set_stopped_notification(int sound_loop_set_id, Uint64 sound_id, gpointer player, TrackState *track) nogil:
    """
    Sends a sound_loop_set stopped notification
    Args:
        sound_loop_set_id: The sound_loop_set id
        sound_id: The sound id
        player: A pointer to the sound loop player that was playing this sound loop set 
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_loop_set_stopped
        notification_message.player = 0
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = 0
        notification_message.data.sound_loop_set.id = sound_loop_set_id
        notification_message.data.sound_loop_set.player = player

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_loop_set_looping_notification(int sound_loop_set_id, Uint64 sound_id, gpointer player, TrackState *track) nogil:
    """
    Sends a sound_loop_set looping notification
    Args:
        sound_loop_set_id: The sound_loop_set id
        sound_id: The sound id
        player: A pointer to the sound loop player that was playing this sound loop set 
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_loop_set_looping
        notification_message.player = 0
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = 0
        notification_message.data.sound_loop_set.id = sound_loop_set_id
        notification_message.data.sound_loop_set.player = player

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

