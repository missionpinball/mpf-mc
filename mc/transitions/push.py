from kivy.animation import AnimationTransition
from kivy.properties import OptionProperty

from mc.uix.transitions import MpfTransition
from kivy.properties import StringProperty


class PushTransition(MpfTransition):
    """Push Transition, the incoming slide "pushes" the existing slide out
    of the frame. Can be used from any direction."""

    direction = OptionProperty('left', options=('left', 'right', 'up', 'down'))
    '''Direction of the transition.

    :attr:`direction` is an :class:`~kivy.properties.OptionProperty` and
    defaults to 'left'. Can be one of 'left', 'right', 'up' or 'down'.
    '''

    easing = StringProperty('linear')

    def on_progress(self, progression):
        sin = self.screen_in
        sout = self.screen_out

        # manager is the parent SlideFrame
        manager = self.manager
        x, y = manager.pos
        width, height = manager.size

        direction = self.direction
        # run the progression (which is 0 -> 1) through the easing formula
        progression = getattr(AnimationTransition, self.easing)(progression)

        if direction == 'left':
            sin.y = sout.y = y
            sin.x = x + width * (1 - progression)
            sout.x = x - width * progression

        elif direction == 'right':
            sin.y = sout.y = y
            sout.x = x + width * progression
            sin.x = x - width * (1 - progression)

        elif direction == 'down':
            sin.x = sout.x = x
            sin.y = y + height * (1 - progression)
            sout.y = y - height * progression

        elif direction == 'up':
            sin.x = sout.x = x
            sout.y = y + height * progression
            sin.y = y - height * (1 - progression)

    def on_complete(self):
        # reset the screen back to its original position
        self.screen_in.pos = self.manager.pos
        self.screen_out.pos = self.manager.pos
        super().on_complete()

        # todo test super().on_complete(). It removes the screen, but is
        # that what we want?


transition_cls = PushTransition
name = 'push'
