"""Magic events for widgets."""
magic_events = ('add_to_slide',
                'remove_from_slide',
                'pre_show_slide',
                'show_slide',
                'pre_slide_leave',
                'slide_leave',
                'slide_play')
"""Magic Events are events that are used to trigger widget actions that
are not real MPF events, rather, they're used to trigger animations from
things the slide is doing."""
