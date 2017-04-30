import importlib
import abc
from typing import TYPE_CHECKING, Optional

from kivy.event import EventDispatcher
from kivy.uix.effectwidget import (MonochromeEffect, InvertEffect,
                                   ScanlinesEffect, ChannelMixEffect,
                                   PixelateEffect, HorizontalBlurEffect,
                                   VerticalBlurEffect, FXAAEffect)

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class EffectsManager(object):
    def __init__(self, mc: "MpfMc") -> None:
        self.mc = mc
        self._effects = dict()
        self._register_mpf_effects()
        self._register_kivy_effects()

    @property
    def effects(self) -> dict:
        return self._effects

    def register_effect(self, name: str, transition_cls) -> None:
        self._effects[name] = transition_cls

    def get_effect(self, effect_config: Optional[str]=None):
        if effect_config:
            # The kivy shader transitions can't accept unexpected kwargs
            kwargs = effect_config.copy()
            kwargs.pop('type')
            return self._effects[effect_config['type']](**kwargs)
        else:
            return None

    def _register_mpf_effects(self) -> None:
        for t in self.mc.machine_config['mpf-mc']['mpf_effect_modules']:
            i = importlib.import_module('mpfmc.effects.{}'.format(t))
            self.register_effect(getattr(i, 'name'),
                                 getattr(i, 'effect_cls'))

    def _register_kivy_effects(self) -> None:
        self.register_effect('monochrome', MonochromeEffect)
        self.register_effect('invert', InvertEffect)
        self.register_effect('scanlines', ScanlinesEffect)
        self.register_effect('channel_mix', ChannelMixEffect)
        self.register_effect('pixelate', PixelateEffect)
        self.register_effect('horizontal_blur', HorizontalBlurEffect)
        self.register_effect('vertical_blur', VerticalBlurEffect)
        self.register_effect('anti_aliasing', FXAAEffect)

    def validate_effects(self, config: dict) -> dict:
        if 'transition' in config:
            if not isinstance(config['transition'], dict):
                config['transition'] = dict(type=config['transition'])

            try:
                config['effect'] = (
                    self.mc.config_validator.validate_config(
                        'effects:{}'.format(config['effect']['type']), config['effect']))

            except KeyError:
                raise ValueError('effect: section of config requires a'
                                 ' "type:" setting')
        else:
            config['effect'] = None

        return config


class EffectsChain(EventDispatcher, metaclass=abc.ABCMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def get_effects(self):
        """Return the list of effects in this chain."""
        raise NotImplementedError('get_effects method must be defined to use this base class')
