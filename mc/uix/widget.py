from kivy.animation import Animation
from kivy.properties import ObjectProperty
from mpf.core.case_insensitive_dict import CaseInsensitiveDict

from mc.core.utils import set_position, percent_to_float


class MpfWidget(object):
    """Mixin class that's used to extend all the Kivy widget base classes with
    a few extra attributes and methods we need for everything to work with MPF.

    """

    widget_type_name = ''  # Give this a name in your subclass, e.g. 'Image'

    # We loop through the keys in a widget's config dict and check to see if
    # the widget's base class has attributes for them, and if so, we set
    # them. This is how any attribute from the base class can be exposed via
    # our configs. However we use some config keys that Kivy also uses,
    # and we use them for different purposes, so there are some keys that we
    # use that we never want to set on widget base classes.
    _dont_send_to_kivy = ('anchor_x', 'anchor_y', 'x', 'y')

    merge_settings = tuple()

    def __init__(self, mc, mode, slide=None, config=None, **kwargs):
        self.size_hint = (None, None)
        super().__init__()

        self.mode = mode
        self.slide = slide
        self.config = config.copy()  # make optional? TODO
        self.mc = mc
        self.animation = None
        self._animation_event_keys = set()

        # some attributes can be expressed in percentages. This dict holds
        # those, key is attribute name, val is max value
        try:
            self._percent_prop_dicts = dict(x=slide.width,
                                            y=slide.height,
                                            width=slide.width,
                                            height=slide.height,
                                            opacity=1,
                                            line_height=1)
        except AttributeError:
            self._percent_prop_dicts = dict()

        for k, v in self.config.items():
            if k not in self._dont_send_to_kivy and hasattr(self, k):
                setattr(self, k, v)

        # This is a weird way to do this, but I don't want to wrap the whole
        # thing in a try block since I don't want to swallow other exceptions.
        if 'animations' in config and config['animations']:
            for k, v in config['animations'].items():
                if k == 'entrance':
                    self.start_animation_from_event('entrance')
                else:
                    self._register_animation_events(k)

    def __repr__(self):  # pragma: no cover
        return '<{} Widget id={}>'.format(self.widget_type_name, self.id)

    def merge_asset_config(self, asset):
        for setting in [x for x in self.merge_settings if (
                        x not in self.config['_default_settings'] and
                        x in asset.config)]:
            self.config[setting] = asset.config[setting]

    def on_size(self, *args):
        try:
            self.pos = set_position(self.parent.width,
                                    self.parent.height,
                                    self.width, self.height,
                                    self.config['x'],
                                    self.config['y'],
                                    self.config['anchor_x'],
                                    self.config['anchor_y'])

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
                try:
                    val = percent_to_float(val, self._percent_prop_dicts[prop])
                except KeyError:
                    # because widget properties can include a % sign, they are
                    # all strings, so even ones that aren't on the list to look
                    # for percent signs have to be converted to numbers.
                    if '.' in val:
                        val = float(val)
                    else:
                        val = int(val)

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

    def update_kwargs(self, **kwargs):
        pass
