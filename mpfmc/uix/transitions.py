import importlib

from kivy.animation import AnimationTransition
from kivy.properties import StringProperty
from kivy.uix.screenmanager import TransitionBase
from kivy.uix.screenmanager import (WipeTransition, SwapTransition,
                                    FadeTransition, FallOutTransition,
                                    RiseInTransition, CardTransition,
                                    NoTransition)


class TransitionManager:
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

    def get_transition(self, transition_config=None):
        if transition_config:
            # The kivy shader transitions can't accept unexpected kwargs
            kwargs = transition_config.copy()
            kwargs.pop('type')
            return self._transitions[transition_config['type']](**kwargs)
        else:
            return NoTransition()

    def _register_mpf_transitions(self):
        for t in self.mc.machine_config['mpf-mc']['mpf_transition_modules']:
            i = importlib.import_module('mpfmc.transitions.{}'.format(t))
            self.register_transition(getattr(i, 'NAME'),
                                     getattr(i, 'TransitionCls'))

    def _register_kivy_transitions(self):
        self.register_transition('wipe', WipeTransition)
        self.register_transition('swap', SwapTransition)
        self.register_transition('fade', FadeTransition)
        self.register_transition('fade_back', FallOutTransition)
        self.register_transition('rise_in', RiseInTransition)
        self.register_transition('card', CardTransition)
        self.register_transition('none', NoTransition)

    def validate_transitions(self, config):

        if 'transition' in config:
            if not isinstance(config['transition'], dict):
                config['transition'] = dict(type=config['transition'])

            try:
                config['transition'] = (
                    self.mc.config_validator.validate_config(
                        'transitions:{}'.format(config['transition']['type']),
                        config['transition']))

            except KeyError:
                raise ValueError('transition: section of config requires a'
                                 ' "type:" setting')
        else:
            config['transition'] = None

        if 'transition_out' in config:
            if not isinstance(config['transition_out'], dict):
                config['transition_out'] = dict(type=config['transition_out'])

            try:
                config['transition_out'] = (
                    self.mc.config_validator.validate_config(
                        'transitions:{}'.format(
                            config['transition_out']['type']),
                        config['transition_out']))

            except KeyError:
                raise ValueError('transition_out: section of config '
                                 'requires a "type:" setting')
        else:
            config['transition_out'] = None

        return config


class MpfTransition(TransitionBase):
    """Base class for slide transitions in MPF. Use this when writing your
    own custom transitions.

    """
    easing = StringProperty('linear')
    """String name of the animation 'easing' function that is used to
    control the shape of the curve of the animation.

    Default is 'linear'.

    """

    def __init__(self, **config):
        # Use ** here instead of dict so this constructor is compatible with
        # the Kivy shader transitions too.

        for k, v in config.items():
            if hasattr(self, k):
                setattr(self, k, v)

        super().__init__()

    def get_vars(self, progression):
        """Convenience method you can call in your own transition's
        on_progress() method to easily get the local vars you need to write
        your own transition.

        Args:
            progression: Float from 0.0 to 1.0 that indicates how far along
            the transition is.

        Returns:
            * Incoming slide object
            * Outgoing slide object
            * Width of the screen
            * Height of the screen
            * Modified progression value (0.0-1.0) which factors in the easing
              setting that has been applied to this transition.

        """
        return (self.screen_in, self.screen_out,
                self.manager.width, self.manager.height,
                getattr(AnimationTransition, self.easing)(progression))

    def on_complete(self):
        # reset the screen back to its original position
        self.screen_in.pos = self.manager.pos
        self.screen_out.pos = self.manager.pos
        super().on_complete()

        # todo test super().on_complete(). It removes the screen, but is
        # that what we want?

    def on_progress(self, progression):
        raise NotImplementedError
