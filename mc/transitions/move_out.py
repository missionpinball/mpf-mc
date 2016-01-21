from kivy.properties import OptionProperty

from mc.uix.transitions import MpfTransition


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

        direction = self.direction

        if direction == 'left':
            # s_in.y = s_out.y
            # s_in.x = width * (1 - progress)
            s_out.x = 0 - width * progress

        elif direction == 'right':
            # s_in.y = s_out.y
            s_out.x = width * progress
            # s_in.x = 0 - width * (1 - progress)

        elif direction == 'down':
            # s_in.x = s_out.x
            # s_in.y = height * (1 - progress)
            s_out.y = 0 - height * progress

        elif direction == 'up':
            # s_in.x = s_out.x
            s_out.y = height * progress
            # s_in.y = 0 - height * (1 - progress)


transition_cls = MoveOutTransition
name = 'move_out'
