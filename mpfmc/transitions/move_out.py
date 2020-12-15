from kivy.properties import OptionProperty

from mpfmc.uix.transitions import MpfTransition


class MoveOutTransition(MpfTransition):
    """Move Out Transition. The current slide moves out of the frame to
    reveal the new slide underneath it"""

    direction = OptionProperty('left', options=('left', 'right', 'top',
                                                'bottom'))

    def start(self, manager):

        super().start(manager)

        # Need to move the new slide so it's below the old one.
        manager.screens.insert(1, manager.screens.pop(0))

    def on_progress(self, progression):

        s_in, s_out, width, height, progress = self.get_vars(progression)

        del s_in

        direction = self.direction

        if direction == 'left':
            s_out.x = 0 - width * progress

        elif direction == 'right':
            s_out.x = width * progress

        elif direction == 'top':
            s_out.y = 0 - height * progress

        elif direction == 'bottom':
            s_out.y = height * progress


TransitionCls = MoveOutTransition
NAME = 'move_out'
