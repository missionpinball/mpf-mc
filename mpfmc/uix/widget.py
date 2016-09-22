from copy import deepcopy

from kivy.animation import Animation
from mpf.core.rgb_color import RGBColor
from kivy.clock import Clock

from mpfmc.core.utils import set_position, percent_to_float

magic_events = ('add_to_slide',
                'remove_from_slide',
                'pre_show_slide',
                'show_slide',
                'pre_slide_leave',
                'slide_leave',
                'slide_play',
                'entrance')
"""Magic Events are events that are used to trigger widget actions that
are not real MPF events, rather, they're used to trigger animations from
things the slide is doing."""


def create_widget_objects_from_config(mc, config, key=None, play_kwargs=None,
                                      widget_settings=None):

    if not isinstance(config, list):
        config = [config]
    widgets_added = list()

    if not play_kwargs:
        play_kwargs = dict()  # todo

    for widget in config:

        if widget_settings:
            widget_settings = mc.config_validator.validate_config(
                'widgets:{}'.format(widget['type']), widget_settings,
                base_spec='widgets:common', add_missing_keys=False)

            widget.update(widget_settings)

        configured_key = widget.get('key', None)

        if (configured_key and key and "." not in key and
                configured_key != key):
            raise KeyError("Widget has incoming key '{}' which does not "
                           "match the key in the widget's config "
                           "'{}'.".format(key, configured_key))

        if configured_key:
            this_key = configured_key
        else:
            this_key = key

        widget_obj = mc.widgets.type_map[widget['type']](
            mc=mc, config=widget, key=this_key, play_kwargs=play_kwargs)

        top_widget = widget_obj

        # some widgets (like slide frames) have parents, so we need to make
        # sure that we add the parent widget to the slide
        while top_widget.parent:
            top_widget = top_widget.parent

        widgets_added.append(top_widget)

    return widgets_added


def create_widget_objects_from_library(mc, name, key=None,
        widget_settings=None, play_kwargs=None, **kwargs):
        if name not in mc.widgets:
            raise ValueError("Widget %s not found", name)

        return create_widget_objects_from_config(mc=mc,
            config=mc.widgets[name], key=key, widget_settings=widget_settings,
                                                 play_kwargs=play_kwargs)


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

    def __init__(self, mc, config=None, key=None, **kwargs):
        del kwargs
        self.size_hint = (None, None)

        super().__init__()

        self.config = deepcopy(config)
        # needs to be deepcopy since configs can have nested dicts

        self.mc = mc

        self.animation = None
        self._animation_event_keys = set()
        # MPF event keys for event handlers that have been registered for
        # animation events. Used to remove the handlers when this widget is
        # removed.

        self._pre_animated_settings = dict()
        # dict of original values of settings that were animated so we can
        # restore them later

        self._percent_prop_dicts = dict()

        self._default_style = None

        self._set_default_style()
        self._apply_style()

        if 'color' in self.config and not isinstance(self.config['color'],
                                                     RGBColor):
            self.config['color'] = RGBColor(self.config['color'])

        for k, v in self.config.items():
            if k not in self._dont_send_to_kivy and hasattr(self, k):
                setattr(self, k, v)

        # Has to be after we set the attributes since it could be in the config
        self.key = key

        self.opacity = self.config.get('opacity', 1.0)

        # This is a weird way to do this, but I don't want to wrap the whole
        # thing in a try block since I don't want to swallow other exceptions.
        if 'animations' in self.config and self.config['animations']:
            for k, v in self.config['animations'].items():
                if k == 'add_to_slide':
                    # needed because the initial properties of the widget
                    # aren't set yet
                    Clock.schedule_once(self.on_add_to_slide, -1)

                elif k == 'entrance':
                    Clock.schedule_once(self.on_add_to_slide, -1)
                    self.mc.log.warning(
                        "DEPRECATION WARNING: The 'entrance' animation event "
                        "name has been changed to 'add_to_slide', "
                        "'pre_show_slide', and/or 'show_slide' to give more "
                        "flexibility. See the docs for more details. "
                        "'entrance' will be removed in 0.32.")

                elif k not in magic_events:
                    self._register_animation_events(k)
        else:
            self.config['animations'] = dict()

        # why is this needed? Why is it not config validated by here? todo
        if 'reset_animations_events' in self.config:
            for event in [x for x in self.config['reset_animations_events']
                    if x not in magic_events]:
                self._animation_event_keys.add(self.mc.events.add_handler(
                    event=event, handler=self.reset_animations))

        self.expire = config.get('expire', None)

        if self.expire:
            self.schedule_removal(self.expire)

    def __repr__(self):  # pragma: no cover
        return '<{} Widget id={}>'.format(self.widget_type_name, self.id)

    def __lt__(self, other):
        return other.config['z'] < self.config['z']

    # todo change to classmethod
    def _set_default_style(self):
        if ('{}_default'.format(self.widget_type_name.lower()) in
                self.mc.machine_config['widget_styles']):
            self._default_style = self.mc.machine_config['widget_styles'][
                '{}_default'.format(self.widget_type_name.lower())]

    def merge_asset_config(self, asset):
        for setting in [x for x in self.merge_settings if (
                        x not in self.config['_default_settings'] and
                        x in asset.config)]:
            self.config[setting] = asset.config[setting]

    def _apply_style(self, force_default=False):
        if not self.config['style'] or force_default:
            if self._default_style:
                style = self._default_style
            else:
                return
        else:
            try:
                style = self.mc.machine_config['widget_styles'][self.config['style'].lower()]
            except KeyError:
                raise ValueError("{} has an invalid style name: {}".format(
                    self, self.config['style'].lower()))

        found = False

        try:
            # This looks crazy but it's not too bad... The list comprehension
            # builds a list of attributes (settings) that are in the style
            # definition but that were not manually set in the widget.

            # Then it sets the attributes directly since the config was already
            # processed.
            for attr in [x for x in style if
                         x not in self.config['_default_settings']]:
                self.config[attr] = style[attr]

            found = True

        except (AttributeError, KeyError):
            pass

        if not found and not force_default:
            self._apply_style(force_default=True)

    def on_size(self, *args):
        del args

        try:
            self.pos = set_position(self.parent.width,
                                    self.parent.height,
                                    self.width, self.height,
                                    self.config['x'],
                                    self.config['y'],
                                    self.config['anchor_x'],
                                    self.config['anchor_y'],
                                    self.config['adjust_top'],
                                    self.config['adjust_right'],
                                    self.config['adjust_bottom'],
                                    self.config['adjust_left'])

        except AttributeError:
            pass

    def on_pos(self, *args):
        del args

        # some attributes can be expressed in percentages. This dict holds
        # those, key is attribute name, val is max value
        try:
            self._percent_prop_dicts = dict(x=self.parent.width,
                                            y=self.parent.height,
                                            width=self.parent.width,
                                            height=self.parent.height,
                                            opacity=1,
                                            line_height=1)
        except AttributeError:
            pass

    def build_animation_from_config(self, config_list):
        """Build animation object from config."""
        if not isinstance(config_list, list):
            raise TypeError('build_animation_from_config requires a list')

        # find any named animations and replace them with the real ones
        animation_list = list()

        for entry in config_list:
            if 'named_animation' in entry:
                for named_anim_settings in (
                        self.mc.animations[entry['named_animation']]):
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

                if prop not in self._pre_animated_settings:
                    self._pre_animated_settings[prop] = getattr(self, prop)

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

    def reset_animations(self, **kwargs):
        del kwargs
        for k, v in self._pre_animated_settings.items():
            setattr(self, k, v)

    def prepare_for_removal(self):
        self.mc.clock.unschedule(self.remove)
        self._remove_animation_events()

    def schedule_removal(self, secs):
        self.mc.clock.schedule_once(self.remove, secs)

    def remove(self, *dt):
        del dt

        try:
            self.parent.remove_widget(self)
        except AttributeError:
            pass

        self.on_remove_from_slide()

    def _register_animation_events(self, event_name):
        self._animation_event_keys.add(self.mc.events.add_handler(
            event=event_name, handler=self.start_animation_from_event,
            event_name=event_name))

    def start_animation_from_event(self, event_name, **kwargs):
        del kwargs

        if event_name not in self.config['animations']:
            return

        self.stop_animation()
        self.animation = self.build_animation_from_config(
            self.config['animations'][event_name])
        self.animation.start(self)

    def _remove_animation_events(self):
        self.mc.events.remove_handlers_by_keys(self._animation_event_keys)
        self._animation_event_keys = set()

    def update_kwargs(self, **kwargs):
        pass

    def on_add_to_slide(self, dt):
        """Automatically called when this widget is added to a slide.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        del dt

        if 'add_to_slide' in self.config['reset_animations_events']:
            self.reset_animations()

        self.start_animation_from_event('entrance')
        self.start_animation_from_event('add_to_slide')

    def on_remove_from_slide(self):
        """Automatically called when this widget is removed from a slide.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'remove_from_slide' in self.config['reset_animations_events']:
            self.reset_animations()

    def on_pre_show_slide(self):
        """Automatically called when the slide this widget is part of is about
        to be shown. If there's an entrance transition, this method is called
        before the transition starts.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'pre_show_slide' in self.config['reset_animations_events']:
            self.reset_animations()

        if 'pre_show_slide' in self.config['animations']:
            self.start_animation_from_event('pre_show_slide')

    def on_show_slide(self):
        """Automatically called when the slide this widget is part of has been
        shown. If there's an entrance transition, this method is called
        after the transition is complete.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'show_slide' in self.config['reset_animations_events']:
            self.reset_animations()

        if 'show_slide' in self.config['animations']:
            self.start_animation_from_event('show_slide')

    def on_pre_slide_leave(self):
        """Automatically called when the slide this widget is part of is about
        to leave (e.g. when another slide is going to replace it). If
        there's an exit transition, this method is called before the
        transition starts.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'pre_slide_leave' in self.config['reset_animations_events']:
            self.reset_animations()

        if 'pre_slide_leave' in self.config['animations']:
            self.start_animation_from_event('pre_slide_leave')

    def on_slide_leave(self):
        """Automatically called when the slide this widget is part of is about
        to leave (e.g. when another slide is going to replace it). If there's
        an exit transition, this method is called after the transition is
        complete.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'slide_leave' in self.config['reset_animations_events']:
            self.reset_animations()

        if 'slide_leave' in self.config['animations']:
            self.start_animation_from_event('slide_leave')

    def on_slide_play(self):
        """Automatically called when the slide this widget is part of is played
        as part of a slide_player play command (either via a standalone slide
        player or as a show step).

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'slide_play' in self.config['reset_animations_events']:
            self.reset_animations()

        if 'slide_play' in self.config['animations']:
            self.start_animation_from_event('slide_play')
