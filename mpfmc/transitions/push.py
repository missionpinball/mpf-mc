from kivy.properties import OptionProperty

from mpfmc.uix.transitions import MpfTransition


class PushTransition(MpfTransition):
    """Push Transition, the incoming slide "pushes" the existing slide out
    of the frame. Can be used from any direction."""

    direction = OptionProperty('left', options=('left', 'right', 'up', 'down'))
    """String name of the direction of the transition.

    Can be 'left', 'right', 'up', or 'down'. Default is 'left'.

    """
    def on_progress(self, progression):

        s_in, s_out, width, height, progress = self.get_vars(progression)

        direction = self.direction

        if direction == 'left':
            s_in.y = s_out.y
            s_in.x = width * (1 - progress)
            s_out.x = 0 - width * progress

        elif direction == 'right':
            s_in.y = s_out.y
            s_out.x = width * progress
            s_in.x = 0 - width * (1 - progress)

        elif direction == 'down':
            s_in.x = s_out.x
            s_in.y = height * (1 - progress)
            s_out.y = 0 - height * progress

        elif direction == 'up':
            s_in.x = s_out.x
            s_out.y = height * progress
            s_in.y = 0 - height * (1 - progress)


TransitionCls = PushTransition
NAME = 'push'
