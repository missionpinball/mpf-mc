from kivy.properties import OptionProperty

from mpfmc.uix.transitions import MpfTransition


class MoveInTransition(MpfTransition):
    """Move In Transition, the current slide does not move, and the
    incoming slide "moves in" on top it."""

    direction = OptionProperty('left', options=('left', 'right', 'top',
                                                'bottom'))

    def on_progress(self, progression):

        s_in, s_out, width, height, progress = self.get_vars(progression)

        del s_out

        direction = self.direction

        if direction == 'left':
            s_in.x = width * (1 - progress)

        elif direction == 'right':
            s_in.x = 0 - width * (1 - progress)

        elif direction == 'top':
            s_in.y = height * (1 - progress)

        elif direction == 'bottom':
            s_in.y = 0 - height * (1 - progress)


TransitionCls = MoveInTransition
NAME = 'move_in'
