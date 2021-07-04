# pylint: disable-msg=too-many-lines
"""A widget on a slide."""
from typing import Union, Optional, List, Tuple
from copy import deepcopy
from functools import reduce
import math

from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget as KivyWidget
from kivy.properties import (NumericProperty, ReferenceListProperty,
                             StringProperty, AliasProperty, ListProperty)

from mpf.core.rgba_color import RGBAColor

from mpfmc.uix.relative_animation import RelativeAnimation
from mpfmc.core.utils import percent_to_float
from mpfmc.uix.widget_magic_events import magic_events

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
class Widget(KivyWidget):
    """MPF-MC Widget class.

    The :class:`Widget` class is the base class required for creating Widgets
    for use in the media controller.  It is based on the Kivy
    kivy.uix.widget.Widget class, but has some custom behavior for use in
    the MC.

    The most important detail is every widget is contained inside another
    specialized widget class (mpfmc.uix.widget.WidgetContainer).  This
    container class is always the parent of a MC Widget and provides the
    coordinate translations to allow MC widgets to use their anchor point
    coordinates instead of the bottom-left corner for all coordinate settings
    (x, y, pos).  The WidgetContainer is automatically created when a widget
    is created and should not be manipulated directly.  It is important to
    remember when walking the widget tree the WidgetContainer is the Widget's
    parent.

    """

    widget_type_name = ''  # Give this a name in your subclass, e.g. 'Image'

    # We loop through the keys in a widget's config dict and check to see if
    # the widget's base class has attributes for them, and if so, we set
    # them. This is how any attribute from the base class can be exposed via
    # our configs. However we use some config keys that Kivy also uses,
    # and we use them for different purposes, so there are some keys that we
    # use that we never want to set on widget base classes.
    _dont_send_to_kivy = ('x', 'y', 'key')

    merge_settings = tuple()

    animation_properties = list()
    """List of properties for this widget that may be animated using widget animations."""

    def __init__(self, mc: "MpfMc", config: Optional[dict] = None,
                 key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        self._container = None
        self.size_hint = (None, None)

        # Needs to be deepcopy since configs can have nested dicts
        self.config = deepcopy(config)

        super().__init__(**self.pass_to_kivy_widget_init())

        self.mc = mc
        self.mc.track_leak_reference(self)

        self.animation = None
        self._animation_event_keys = set()
        # MPF event keys for event handlers that have been registered for
        # animation events. Used to remove the handlers when this widget is
        # removed.

        self._pre_animated_settings = dict()
        # dict of original values of settings that were animated so we can
        # restore them later

        self._percent_prop_dicts = dict()

        self._round_anchor_styles = (None, None)

        self._default_style = None
        self._set_default_style()
        self._apply_style()

        # Create a container widget as this widget's parent.  The container will adjust
        # the coordinate system for this widget so that all positional properties are
        # based on the widget's anchor rather than the lower left corner.
        self._container = WidgetContainer(self, z=self.config['z'])
        self._container.add_widget(self)
        self._container.fbind('parent', self.on_container_parent)

        if 'color' in self.config and not isinstance(self.config['color'], RGBAColor):
            self.config['color'] = RGBAColor(self.config['color'])

        # Set initial attribute values from config
        for k, v in self.config.items():
            if k not in self._dont_send_to_kivy and hasattr(self, k):
                setattr(self, k, v)

        # Has to be after we set the attributes since it could be in the config
        self.key = key

        # Build animations
        if 'animations' in self.config and self.config['animations']:
            for k, v in self.config['animations'].items():
                if k.split("{")[0] == 'add_to_slide':
                    # needed because the initial properties of the widget
                    # aren't set yet
                    Clock.schedule_once(self.on_add_to_slide, -1)

                elif k not in magic_events:
                    self._register_animation_events(k)
        else:
            self.config['animations'] = dict()

        # why is this needed? Why is it not config validated by here? todo
        if 'reset_animations_events' in self.config:
            for event in [x for x in self.config['reset_animations_events'] if x not in magic_events]:
                self._animation_event_keys.add(self.mc.events.add_handler(
                    event=event, handler=self.reset_animations))

        # Set widget expiration (if configured)
        self.expire = config.get('expire', None)
        if self.expire:
            self.schedule_removal(self.expire)

        # Send custom user events when widget is added (if any are configured)
        if self.config['events_when_added'] is not None:
            for event in self.config['events_when_added']:
                self.mc.post_mc_native_event(event)

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} Widget id={}>'.format(self.widget_type_name, id(self))

    @staticmethod
    def get_display():
        """Get the display used"""
        return None

    @staticmethod
    def pass_to_kivy_widget_init() -> dict:
        """Initializes the dictionary of settings to pass to Kivy."""
        return dict()

    def merge_asset_config(self, asset) -> None:
        for setting in [x for x in self.merge_settings if (
                        x not in self.config['_default_settings'] and
                        x in asset.config)]:
            self.config[setting] = asset.config[setting]

    def on_anchor_offset_pos(self, instance, pos):
        """Called whenever the anchor_offset_pos property value changes."""
        del instance
        if self.parent:
            self.parent.pos = pos

    def on_container_parent(self, instance, parent):
        del instance
        if parent:
            # some attributes can be expressed in percentages. This dict holds
            # those, key is attribute name, val is max value

            self._percent_prop_dicts = dict(x=parent.width,
                                            y=parent.height,
                                            width=parent.width,
                                            height=parent.height,
                                            opacity=1,
                                            line_height=1)

            # The top-most parent owns the display, so traverse up to find the config
            top_widget = parent
            while not hasattr(top_widget, "display") and top_widget.parent != top_widget and top_widget.parent:
                print(top_widget)
                top_widget = top_widget.parent
            displayconfig = top_widget.display.config if hasattr(top_widget, 'display') else dict()

            # If the positioning is centered, look for a rounding setting to avoid
            # fractional anchor positions. Fallback to display's config if available
            round_anchor_x = self.config['round_anchor_x'] or displayconfig.get('round_anchor_x')
            round_anchor_y = self.config['round_anchor_y'] or displayconfig.get('round_anchor_y')

            # Store the anchor rounding config from widget/display to avoid recalculation
            self._round_anchor_styles = (round_anchor_x, round_anchor_y)

            self.pos = self.calculate_initial_position(parent.width,
                                                       parent.height,
                                                       self.config['x'],
                                                       self.config['y'],
                                                       round_anchor_x,
                                                       round_anchor_y)

            # Update the initial widget position based on the rounding config
            self.pos = self.calculate_rounded_position(self.anchor_offset_pos)

    def calculate_rounded_position(self, anchor: Tuple[int, int]) -> tuple:
        """Returns a tuple of (x, y) coordinates for the position of the widget,
        accounting for odd-numbered pixel dimensions and the rounding configuration
        of the widget/display."""
        # Start with the given initial position of the widget
        rounded_x = self.pos[0]
        rounded_y = self.pos[1]

        # Shift each of the x/y coordinates according to the anchor rounding
        if self._round_anchor_styles[0] == 'left':
            rounded_x -= anchor[0] % 1
        elif self._round_anchor_styles[0] == 'right':
            rounded_x += (1 - anchor[0]) % 1
        if self._round_anchor_styles[1] == 'bottom':
            rounded_y -= anchor[1] % 1
        elif self._round_anchor_styles[1] == 'top':
            rounded_y += (1 - anchor[1]) % 1

        return rounded_x, rounded_y

    @staticmethod
    def _calculate_x_position(parent_w: int, x: Optional[Union[int, str]] = None,
                              round_x: Optional[Union[bool, str]] = None) -> float:
        # ----------------------
        # X / width / horizontal
        # ----------------------
        if x is None:
            x = 'center'
        # Calculate position
        if isinstance(x, str):

            x = str(x).replace(' ', '')
            start_x = 0

            if x.startswith('right'):
                x = x.strip('right')
                start_x = parent_w

            elif x.startswith('middle'):
                x = x.strip('middle')
                start_x = parent_w / 2

            elif x.startswith('center'):
                x = x.strip('center')
                start_x = parent_w / 2

            elif x.startswith('left'):
                x = x.strip('left')

            if not x:
                x = '0'

            x = percent_to_float(x, parent_w)
            x += start_x

            if round_x == 'left':
                x = math.floor(x)
            elif round_x == 'right':
                x = math.ceil(x)

        return x

    @staticmethod
    def _calculate_y_position(parent_h: int, y: Optional[Union[int, str]] = None,
                              round_y: Optional[Union[bool, str]] = None) -> float:
        # Set defaults
        if y is None:
            y = 'middle'

        # --------------------
        # Y / height / vertical
        # --------------------

        # Calculate position
        if isinstance(y, str):

            y = str(y).replace(' ', '')
            start_y = 0

            if y.startswith('top'):
                y = y.strip('top')
                start_y = parent_h

            elif y.startswith('middle'):
                y = y.strip('middle')
                start_y = parent_h / 2

            elif y.startswith('center'):
                y = y.strip('center')
                start_y = parent_h / 2

            elif y.startswith('bottom'):
                y = y.strip('bottom')

            if not y:
                y = '0'

            y = percent_to_float(y, parent_h)
            y += start_y

            if round_y == 'bottom':
                y = math.floor(y)
            elif round_y == 'top':
                y = math.ceil(y)

        return y

    # pylint: disable-msg=too-many-arguments
    @classmethod
    def calculate_initial_position(cls, parent_w: int, parent_h: int,
                                   x: Optional[Union[int, str]] = None,
                                   y: Optional[Union[int, str]] = None,
                                   round_x: Optional[Union[bool, str]] = None,
                                   round_y: Optional[Union[bool, str]] = None) -> Tuple[float, float]:
        """Returns the initial x,y position for the widget within a larger
        parent frame based on several positioning parameters. This position will
        be combined with the widget anchor position to determine its actual
        position on the screen.

        Args:
            parent_w: Width of the parent frame.
            parent_h: Height of the parent frame.
            x: (Optional) Specifies the x (horizontal) position of the widget from
                the left edge of the slide. Can be a numeric value which
                represents the actual x value, or can be a percentage (string with
                percent sign, like '20%') which is set taking into account the size
                of the parent width. (e.g. parent width of 800 with x='20%'
                results in x=160. Can also be negative to position the widget
                partially off the left of the slide. Default value of None will
                return the horizontal center (parent width / 2). Can also start
                with the strings "left", "center", or "right" which can be combined
                with values. (e.g right-2, left+4, center-1)
            y: (Optional) Specifies the y (vertical) position of the widget from
                the bottom edge of the slide. Can be a numeric value which
                represents the actual y value, or can be a percentage (string with
                percent sign, like '20%') which is set taking into account the size
                of the parent height. (e.g. parent height of 600 with y='20%'
                results in y=120. Can also be negative to position the widget
                partially off the bottom of the slide. Default value of None will
                return the vertical center (parent height / 2). Can also start
                with the strings "top", "middle", or "bottom" which can be combined
                with values. (e.g top-2, bottom+4, middle-1)
            round_x: (Optional) Specifies a direction of either "left" or "right"
                to round the calculated pixel value for the horizontal position.
                Used to prevent partial pixel placement on DMDs, especially when
                position/anchors are specified in percentages
            round_y: (Optional) Specifies a direction of either "bottom" or "top"
                to round the calculated pixel value for the vertical position.
                Used to prevent partial pixel placement on DMDs, especially when
                position/anchors are specified in percentages

        Returns: Tuple of x, y coordinates for the lower-left corner of the
            widget you're placing.

        See the widgets documentation for examples.

        """
        return cls._calculate_x_position(parent_w, x, round_x), cls._calculate_y_position(parent_h, y, round_y)

    def _set_default_style(self) -> None:
        """Sets the default widget style name."""
        if ('{}_default'.format(self.widget_type_name.lower()) in
                self.mc.machine_config['widget_styles']):
            self._default_style = self.mc.machine_config['widget_styles'][
                '{}_default'.format(self.widget_type_name.lower())]

    def _apply_style(self, force_default: bool = False) -> None:
        """Apply any style to the widget that is specified in the config."""
        if not self.config['style'] or force_default:
            if self._default_style:
                styles = [self._default_style]
            else:
                return
        else:
            try:
                styles = [self.mc.machine_config['widget_styles'][s] for s in self.config['style']]
            except KeyError as e:
                # TOOD: After sufficient time post-0.51, remove this breaking-change-related message
                if " ".join(self.config['style']) in self.mc.machine_config['widget_styles']:
                    raise ValueError("{} has an invalid style name: {}. ".format(self, e) +
                                     "Please note that as of MPF 0.51, spaces are no longer valid " +
                                     "in widget style names (see '{}')".format(" ".join(self.config['style'])))
                raise ValueError("{} has an invalid style name: {}".format(
                    self, e))

        found = False

        try:
            # This looks crazy but it's not too bad... The list comprehension
            # builds a list of attributes (settings) that are in the style
            # definition but that were not manually set in the widget.

            # Then it sets the attributes directly since the config was already
            # processed.
            for style in styles:
                for attr in [x for x in style if
                             x not in self.config['_default_settings']]:
                    self.config[attr] = style[attr]

            found = True

        except (AttributeError, KeyError):
            pass

        if not found and not force_default:
            self._apply_style(force_default=True)

    def prepare_for_removal(self) -> None:
        """Prepare the widget to be removed."""
        self.mc.clock.unschedule(self.remove)
        self.stop_animation()
        self._remove_animation_events()

        # Send custom user events when widget is removed (if any are configured)
        if self.config['events_when_removed'] is not None:
            for event in self.config['events_when_removed']:
                self.mc.post_mc_native_event(event)

    def schedule_removal(self, secs: float) -> None:
        """Schedule the widget to be removed after the specified number
        of seconds have elapsed."""
        self.mc.clock.schedule_once(self.remove, secs)

    def remove(self, *dt) -> None:
        """Perform the actual removal of the widget."""
        del dt

        self.prepare_for_removal()

        try:
            # This widget has a container parent that must be removed
            self._container.parent.remove_widget(self._container)
        except AttributeError:
            pass

        self.on_remove_from_slide()

    def _convert_animation_value_to_float(self, prop: str,
                                          val: Union[str, int, float], event_args) -> Union[float, int]:
        """
        Convert an animation property value to a numeric value.
        Args:
            prop: The name of the property to animate
            val: The animation target value (may be a string that contains a % sign)

        Returns:
            Numeric value (float or int).
        """
        if val.startswith("(") and val.endswith(")"):
            if val[1:-1].startswith("machine|"):
                val = self.mc.machine_vars.get(val[9:-1], 0)
            else:
                try:
                    val = event_args[val[1:-1]]
                except KeyError:
                    raise AssertionError("Excepted an event parameter {}".format(val[1:-1]))

        try:
            val = percent_to_float(val, self._percent_prop_dicts[prop])
        except KeyError:
            # because widget properties can include a % sign, they are
            # often strings, so even ones that aren't on the list to look
            # for percent signs have to be converted to numbers.
            if '.' in str(val):
                val = float(val)
            else:
                val = int(val)

        return val

    def _resolve_named_animations(self, config_list):
        # find any named animations and replace them with the real ones
        animation_list = list()

        for entry in config_list:
            if 'named_animation' in entry:
                for named_anim_settings in (
                        self.mc.animations[entry['named_animation']]):
                    animation_list.append(named_anim_settings)
            else:
                animation_list.append(entry)

        return animation_list

    # pylint: disable-msg=too-many-branches
    # pylint: disable-msg=too-many-locals
    def build_animation_from_config(self, config_list: list, event_args) -> Animation:
        """Build animation object from config."""
        if not isinstance(config_list, list):
            raise TypeError('build_animation_from_config requires a list')

        # find any named animations and replace them with the real ones
        animation_list = self._resolve_named_animations(config_list)

        repeat = False
        animation_sequence_list = []

        for settings in animation_list:
            prop_dict = dict()
            values_needed = dict()
            values = settings['value'].copy()

            # Some properties that can be animated contain more than single values
            # (such as color). Need to ensure there are the correct number of
            # values for the properties to animate.
            values_needed_total = 0

            for prop in settings['property']:
                if isinstance(getattr(self, prop), list):
                    values_needed[prop] = len(getattr(self, prop))
                    values_needed_total += values_needed[prop]
                else:
                    values_needed[prop] = 1
                    values_needed_total += 1

            if len(settings['value']) != values_needed_total:
                self.mc.log.warning("There is a mismatch between the number of values "
                                    "available and the number of values required to animate "
                                    "the following properties in the %s widget: %s "
                                    "(animation will be ignored).",
                                    self.widget_type_name, settings['property'])
                continue

            # Create a dictionary of properties to animate along with their target values
            for prop in settings['property']:

                # Make sure target widget property can be animated
                if prop not in self.animation_properties:
                    self.mc.log.warning("%s widgets do not support animation "
                                        "for the %s property (animation will be ignored)",
                                        self.widget_type_name, prop)
                    continue

                # Convert target value(s) to numeric types
                if values_needed[prop] > 1:
                    val = [self._convert_animation_value_to_float(prop, x, event_args)
                           for x in values[:values_needed[prop]]]
                    del values[:values_needed[prop]]
                else:
                    val = self._convert_animation_value_to_float(prop, values[0], event_args)
                    del values[0]

                prop_dict[prop] = val

                # Save the pre-animated property value so it can later be restored
                if prop not in self._pre_animated_settings:
                    self._pre_animated_settings[prop] = getattr(self, prop)

            # TODO: Support custom easing functions
            # This can be done by replacing transition string with a function reference
            # when the string does not exist in the Kivy AnimationTransition class as
            # a method.

            # Create the animation object
            if settings['relative']:
                animation = RelativeAnimation(duration=settings['duration'],
                                              transition=settings['easing'],
                                              **prop_dict)
            else:
                animation = Animation(duration=settings['duration'],
                                      transition=settings['easing'],
                                      **prop_dict)

            # Determine if this animation should be performed in sequence or in parallel
            # with the previous animation.
            if settings['timing'] == 'with_previous' and animation_sequence_list:
                # Combine in parallel with previous animation
                animation_sequence_list[-1] &= animation
            else:
                # Add new sequential animation to the list
                animation_sequence_list.append(animation)

            if settings['repeat']:
                repeat = True

        # Combine all animations that should be performed in sequence into a single
        # animation object (add them all together)
        final_animation = reduce(lambda x, y: x + y, animation_sequence_list)

        if repeat:
            final_animation.repeat = True

        return final_animation

    def stop_animation(self) -> None:
        """Stop the current widget animation."""
        try:
            self.animation.cancel(self)
        except AttributeError:
            pass

    def reset_animations(self, **kwargs) -> None:
        """Reset the widget properties back to their pre-animated values."""
        del kwargs
        for k, v in self._pre_animated_settings.items():
            setattr(self, k, v)

    def _register_animation_events(self, event_name: str) -> None:
        """Register handlers for the various events that trigger animation actions."""
        self._animation_event_keys.add(self.mc.events.add_handler(
            event=event_name, handler=self.start_animation_from_event,
            event_name=event_name))

    def start_animation_from_event(self, event_name: str, **kwargs) -> None:
        """Starts an animation based on an event name that has previously
        been registered."""
        if event_name not in self.config['animations']:
            return

        self.stop_animation()
        self.animation = self.build_animation_from_config(
            self.config['animations'][event_name], kwargs)
        self.animation.start(self)

    def _remove_animation_events(self) -> None:
        """Remove previously registered handlers for the various events that trigger animation actions."""
        self.mc.events.remove_handlers_by_keys(self._animation_event_keys)
        self._animation_event_keys = set()

    def on_add_to_slide(self, dt) -> None:
        """Automatically called when this widget is added to a slide.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        del dt

        if 'add_to_slide' in self.config['reset_animations_events']:
            self.reset_animations()

        for k in self.config['animations'].keys():
            event, placeholder, _ = self.mc.events.get_event_and_condition_from_string(k)
            if event == 'add_to_slide' and (not placeholder or placeholder.evaluate({})):
                self.start_animation_from_event(k)
                break

    def on_remove_from_slide(self) -> None:
        """Automatically called when this widget is removed from a slide.

        If you subclass this method, be sure to call super(), as it's needed
        for widget animations.
        """
        if 'remove_from_slide' in self.config['reset_animations_events']:
            self.reset_animations()

    def on_pre_show_slide(self) -> None:
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

    def on_show_slide(self) -> None:
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

    def on_pre_slide_leave(self) -> None:
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

    def on_slide_leave(self) -> None:
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

    def on_slide_play(self) -> None:
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

    def find_widgets_by_key(self, key: str) -> List["KivyWidget"]:
        """Return a list of widgets with the matching key value by searching
        the tree of children belonging to this widget."""
        return [x for x in self.walk(restrict=True, loopback=False) if hasattr(x, 'key') and x.key == key]

    #
    # Properties
    #

    def _get_container(self) -> KivyWidget:
        return self._container

    container = AliasProperty(_get_container, None)
    '''The widget container is a special container/parent widget that manages this widget.
    It has no graphical representation.'''

    key = StringProperty(None, allownone=True)
    '''Widget keys are used to uniquely identify instances of widgets which you can later
    use to update or remove the widget.
    '''

    color = ListProperty([1.0, 1.0, 1.0, 1.0])
    '''The color of the widget, in the (r, g, b, a) format.

    :attr:`color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [1.0, 1.0, 1.0, 1.0].
    '''

    anchor_x = StringProperty(None, allownone=True)
    '''Which edge of the widget will be used for positioning. ('left', 'center'
    (or 'middle'), or 'right'. If None, 'center' will be used.
    '''

    anchor_y = StringProperty(None, allownone=True)
    '''Which edge of the widget will be used for positioning. ('top', 'middle'
    (or 'center'), or 'bottom'. If None, 'center' will be used.
    '''

    anchor_pos = ReferenceListProperty(anchor_x, anchor_y)
    '''Which point of the widget will be used for positioning.

    :attr:`anchor_pos` is a :class:`~kivy.properties.ReferenceListProperty`
    of (:attr:`anchor_x`, :attr:`anchor_y`) properties.
    '''

    adjust_top = NumericProperty(0)
    '''Moves the "top" of this widget's anchor position down, meaning any
    positioning that includes calculations involving the top (anchor_y of 'top'
    or 'middle') use the alternate top position. Positive values move the top
    towards the center of the widget, negative values move it away. Negative
    values can be used to give the widget "space" on the top, and positive
    values can be used to remove unwanted space from the top of the widget.
    Note that this setting does not actually crop or cut off the top of the
    widget, rather, it just adjusts how the positioning is calculated.
    '''

    adjust_right = NumericProperty(0)
    '''Adjusts the anchor position calculations for the right side of the widget.
    Positive values move the right position  towards the center, negative values
    move it away from the center.
    '''

    adjust_bottom = NumericProperty(0)
    '''Adjusts the anchor position calculations for the bottom of the widget.
    Positive values move the bottom position towards the center, negative values
    move it away from the center.
    '''

    adjust_left = NumericProperty(0)
    '''Adjusts the anchor position calculations for the left side of the widget.
    Positive values move the left position towards the center, negative values
    move it away from the center.
    '''

    def _get_anchor_offset_pos(self):
        """Calculate the anchor offset position relative to the lower-left corner of the widget.

        Based on several positioning parameters.
        """
        # Set defaults
        offset_x = 0
        offset_y = 0
        anchor_x = self.anchor_x
        anchor_y = self.anchor_y
        if not anchor_x:
            anchor_x = 'center'
        if not self.anchor_y:
            anchor_y = 'middle'

        # ----------------------
        # X / width / horizontal
        # ----------------------

        # Adjust for anchor_x & adjust_right/left
        if anchor_x in ('center', 'middle'):
            offset_x -= (self.width - self.adjust_right + self.adjust_left) / 2
        elif anchor_x == 'right':
            offset_x -= self.width - self.adjust_right
        else:  # left
            offset_x -= self.adjust_left

        # --------------------
        # Y / height / vertical
        # --------------------

        # Adjust for anchor_y & adjust_top/bottom
        if anchor_y in ('middle', 'center'):
            offset_y -= (self.height - self.adjust_top + self.adjust_bottom) / 2
        elif anchor_y == 'top':
            offset_y -= self.height - self.adjust_top
        else:  # bottom
            offset_y -= self.adjust_bottom

        return offset_x, offset_y

    anchor_offset_pos = AliasProperty(_get_anchor_offset_pos, None,
                                      bind=('size', 'anchor_x', 'anchor_y', 'adjust_top',
                                            'adjust_right', 'adjust_bottom', 'adjust_left'),
                                      cache=True)
    '''The anchor position of the widget (relative to the widget's lower left corner).

    :attr:`anchor_offset_pos` is a :class:`~kivy.properties.ReferenceListProperty`
    of (:attr:`anchor_offset_x`, :attr:`anchor_offset_y`) properties.
    '''


def create_widget_objects_from_config(mc: "MpfMc", config: Union[dict, list],
                                      key: Optional[str] = None,
                                      play_kwargs: Optional[dict] = None,
                                      widget_settings: Optional[dict] = None) -> List["WidgetContainer"]:
    """
    Creates one or more widgets from config settings.

    Args:
        mc: An instance of MC
        config: The configuration dictionary for the widgets to be created.
        key: An optional key.
        play_kwargs: An optional dictionary of play settings to override those in
            the config.
        widget_settings: An optional dictionary of widget settings to override those in
            the config.

    Returns:
        A list of the WidgetContainer objects created.
    """
    if not isinstance(config, list):
        config = [config]
    widgets_added = list()

    if not play_kwargs:
        play_kwargs = dict()  # todo

    for widget in config:
        # Lookup a pre-defined widget based on a name
        name = widget.get('widget', None)
        if name:
            widgets_added += create_widget_objects_from_library(name=name,
                                                                mc=mc,
                                                                play_kwargs=play_kwargs,
                                                                widget_settings=widget_settings)
            continue
        if widget_settings:
            widget_settings = mc.config_validator.validate_config(
                'widgets:{}'.format(widget['type']), widget_settings,
                base_spec='widgets:common', add_missing_keys=False)

            widget.update(widget_settings)

        configured_key = widget.get('key', None)

        if configured_key and key and "." not in key and configured_key != key:
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

        # some widgets have parents, so we need to make sure that we add
        # the parent widget to the slide
        while top_widget.parent:
            top_widget = top_widget.parent

        widgets_added.append(top_widget)

    return widgets_added


def create_widget_objects_from_library(mc: "MpfMc", name: str,
                                       key: Optional[str] = None,
                                       widget_settings: Optional[dict] = None,
                                       play_kwargs: Optional[dict] = None,
                                       **kwargs) -> List["WidgetContainer"]:
    """

    Args:
        mc:
        name:
        key:
        widget_settings:
        play_kwargs:
        **kwargs:

    Returns:
        A list of the MpfWidget objects created.
    """
    del kwargs

    # If the name is a placeholder template, evaluate it against the args
    if name and hasattr(name, "evaluate"):
        name = name.evaluate(play_kwargs)

    if name not in mc.widgets:
        raise ValueError("Widget {} not found".format(name))

    return create_widget_objects_from_config(mc=mc,
                                             config=mc.widgets[name],
                                             key=key,
                                             widget_settings=widget_settings,
                                             play_kwargs=play_kwargs)


class WidgetContainer(RelativeLayout):

    def __init__(self, widget: "Widget",
                 key: Optional[str] = None, z: int = 0, **kwargs) -> None:
        del kwargs
        self.key = None
        super().__init__(size_hint=(1, 1))

        self.key = key
        self.z = z
        self._widget = widget

    def __repr__(self) -> str:  # pragma: no cover
        return '<WidgetContainer z={} key={}>'.format(self.z, self.key)

    def __lt__(self, other: "KivyWidget") -> bool:
        """Less than comparison operator (based on z-order value).

        Used to maintain proper z-order when adding widgets to a parent.
        Args:
            other: The widget to compare to this one.

        Returns:
            True if the other widget is less than the current widget (uses
            z-order to perform the comparison).
        """
        if hasattr(other, 'z'):
            return other.z < self.z
        else:
            return self.z > 0

    def prepare_for_removal(self) -> None:
        if self._widget:
            self._widget.prepare_for_removal()

    def on_pre_show_slide(self) -> None:
        if self._widget:
            self._widget.on_pre_show_slide()

    def on_show_slide(self) -> None:
        if self._widget:
            self._widget.on_show_slide()

    def on_pre_slide_leave(self) -> None:
        if self._widget:
            self._widget.on_pre_slide_leave()

    def on_slide_leave(self) -> None:
        if self._widget:
            self._widget.on_slide_leave()

    def on_slide_play(self) -> None:
        if self._widget:
            self._widget.on_slide_play()

    #
    # Properties
    #

    z = NumericProperty(0)
    '''Z position (z-order) of the widget (used to determine the drawing order of widgets).
    '''

    def get_display(self):
        """Get the display used"""
        return self._widget.get_display()

    def _get_widget(self):
        return self._widget

    widget = AliasProperty(_get_widget, None)
    '''The MC Widget child of this container widget.'''
