import importlib

from kivy.properties import StringProperty
from kivy.uix.screenmanager import WipeTransition, SwapTransition, \
    FadeTransition, FallOutTransition, RiseInTransition
from kivy.uix.screenmanager import TransitionBase, ScreenManagerException
from kivy.animation import Animation

class TransitionManager(object):
    def __init__(self, mc):
        self.mc = mc
        self._transitions = dict()

        self._register_mpf_transitions()
        self._register_kivy_transitions()

    @property
    def transitions(self):
        return self._transitions

    def register_transition(self, name, transition_cls):
        self._transitions[name] = transition_cls

    def set_transition(self, target, transition_config=None):

        if transition_config:
            target.transition = self._transitions[transition_config['type']](
                    **transition_config)

        else:
            pass
        # set default? Or use current?


    def _register_mpf_transitions(self):
        for t in self.mc.machine_config['mpf_mc']['mpf_transition_modules']:
            i = importlib.import_module('mc.transitions.{}'.format(t))
            self.register_transition(getattr(i, 'name'),
                                     getattr(i, 'transition_cls'))

    def _register_kivy_transitions(self):
        self.register_transition('wipe', WipeTransition)
        self.register_transition('swap', SwapTransition)
        self.register_transition('fade', FadeTransition)
        self.register_transition('fade_back', FallOutTransition)
        self.register_transition('rise_in', RiseInTransition)


class MpfTransition(TransitionBase):

    easing = StringProperty('linear')

    def __init__(self, **config):
        # Use ** here instead of dict so this constructor is compatible with
        # the Kivy shader transitions too.

        for k, v in config.items():
            if hasattr(self, k):
                setattr(self, k, v)

        super().__init__()

    def start(self, manager):

        if self.is_active:
            raise ScreenManagerException('start() is called twice!')
        self.manager = manager
        self._anim = Animation(d=self.duration, s=0)
        self._anim.bind(on_progress=self._on_progress,
                        on_complete=self._on_complete)

        self.add_screen(self.screen_in)
        self.screen_in.transition_progress = 0.
        self.screen_in.transition_state = 'in'
        self.screen_out.transition_progress = 0.
        self.screen_out.transition_state = 'out'
        self.screen_in.dispatch('on_pre_enter')
        self.screen_out.dispatch('on_pre_leave')

        self.is_active = True
        self._anim.start(self)
        self.dispatch('on_progress', 0)
