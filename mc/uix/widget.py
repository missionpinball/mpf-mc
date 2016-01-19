from copy import deepcopy

from kivy.animation import Animation
from kivy.properties import ObjectProperty
from mpf.system.config import CaseInsensitiveDict

from mc.core.utils import set_position


class MpfWidget(object):
    """Mixin class that's used to extend all the Kivy widget base classes with
    a few extra attributes and methods we need for everything to work with MPF.

    """
    mode = ObjectProperty(None, allownone=True)
    """:class:`Mode` object, which is the mode that created this widget."""

    config = CaseInsensitiveDict()
    """Dict which holds the settings for this widget."""

    slide = None
    """Slide that this widget will be used with."""

    def __init__(self, mc, mode, slide=None, config=None, **kwargs):
        self.size_hint = (None, None)
        super().__init__()

        self.mode = mode
        self.slide = slide
        self.config = config
        self.mc = mc
        self.ready = False
        self.animation = None
        self._animation_event_keys = set()

        for k, v in self.config.items():
            if hasattr(self, k):
                setattr(self, k, v)

        # This is a weird way to do this, but I don't want to wrap the whole
        # thing in a try block since I don't want to swallow other exceptions.
        if 'animations' in config and config['animations']:
            for k, v in config['animations'].items():
                if k == 'entrance':
                    self.start_animation_from_event('entrance')
                else:
                    self._register_animation_events(k)

    def __repr__(self):
        return '<{} Widget id={}>'.format(self.widget_type_name, self.id)

    def on_size(self, *args):
        try:
            self.pos = set_position(self.parent.width,
                                    self.parent.height,
                                    self.width, self.height,
                                    self.config['x'],
                                    self.config['y'],
                                    self.config['h_pos'],
                                    self.config['v_pos'])
        except AttributeError:
            pass

    def build_animation_from_config(self, config_list):

        if not isinstance(config_list, list):
            raise TypeError('build_animation_from_config requires a list')

        # find any named animations and replace them with the real ones
        animation_list = list()

        for entry in config_list:
            if 'named_animation' in entry:

                for named_anim_settings in self.mc.animation_configs[entry[
                        'named_animation']]:
                    animation_list.append(named_anim_settings)

            else:
                animation_list.append(entry)

        final_anim = None
        repeat = False

        for settings in animation_list:
            prop_dict = dict()
            for prop, val in zip(settings['property'], settings['value']):
                prop_dict[prop] = val

            anim = Animation(duration=settings['duration'],
                             transition=settings['easing'],
                             **prop_dict)

            if not final_anim:
                final_anim = anim
            elif settings['timing'] == 'with_previous':
                final_anim &= anim
            elif settings['timing'] == 'after_previous':
                final_anim += anim

            if settings['repeat']:
                repeat = True

        if repeat:
            final_anim.repeat = True

        return final_anim

    def stop_animation(self):
        try:
            self.animation.stop(self)
        except AttributeError:
            pass

    def play_animation(self):
        try:
            self.animation.play(self)
        except AttributeError:
            pass

    def prepare_for_removal(self, widget):
        self._remove_animation_events()

    def _register_animation_events(self, event_name):
        self._animation_event_keys.add(self.mc.events.add_handler(
                event=event_name, handler=self.start_animation_from_event,
                event_name=event_name))

    def start_animation_from_event(self, event_name, **kwargs):
        self.stop_animation()
        self.animation = self.build_animation_from_config(
                self.config['animations'][event_name])
        self.animation.start(self)

    def _remove_animation_events(self):
        self.mc.events.remove_handlers_by_keys(self._animation_event_keys)
        self._animation_event_keys = set()
