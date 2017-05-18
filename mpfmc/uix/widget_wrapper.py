'''
WidgetWrapper
=============

:class:`WidgetWrapper` is a class designed to wrap widgets for use in MPF-MC.

The WidgetWrapper uses a kivy.uix.relativelayout.RelativeLayout to provide a 
transformed coordinate system so that MPF-MC widgets can be interacted with 
using their designated anchor point rather than the lower-left corner. This 
has the benefit of being able to animate the positional properties directly 
using the anchor point. The actual widget is a child of the WidgetWrapper 
class.

'''

from copy import deepcopy
from functools import reduce
from typing import List, Union, Optional, TYPE_CHECKING

from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import NumericProperty, StringProperty, AliasProperty
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout

from mpfmc.core.utils import percent_to_float
from mpfmc.uix.relative_animation import RelativeAnimation
from mpf.core.rgba_color import RGBAColor

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc

magic_events = ('add_to_slide',
                'remove_from_slide',
                'pre_show_slide',
                'show_slide',
                'pre_slide_leave',
                'slide_leave',
                'slide_play')
"""Magic Events are events that are used to trigger widget actions that
are not real MPF events, rather, they're used to trigger animations from
things the slide is doing."""


class WidgetWrapper(RelativeLayout):

    widget_type_name = ''  # Give this a name in your subclass, e.g. 'Image'

    # We loop through the keys in a widget's config dict and check to see if
    # the widget's base class has attributes for them, and if so, we set
    # them. This is how any attribute from the base class can be exposed via
    # our configs. However we use some config keys that Kivy also uses,
    # and we use them for different purposes, so there are some keys that we
    # use that we never want to set on widget base classes.
    _dont_send_to_kivy = ('anchor_x', 'anchor_y', 'x', 'y', 'scale', 'rotation')

    merge_settings = tuple()

    animation_properties = list()
    """List of properties for this widget that may be animated using widget animations.
    The wrapped/managed child widget must support these properties."""

    def __init__(self, mc: "MpfMc", config: Optional[dict]=None,
                 key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        self.size_hint = (1, 1)
        super().__init__()

        # Deepcopy config since configs can have nested dicts
        self.config = deepcopy(config)

        self.mc = mc

        # self._widget contains the widget that is wrapped/managed by this WidgetWrapper class
        self._widget = self._create_child_widget()
        self._bind_child_widget_properties(self._widget)
        self.add_widget(self._widget)
        self.pos = self.calculate_anchor_offset(self._widget.width, self._widget.height,
                                                self.config['anchor_x'],
                                                self.config['anchor_y'],
                                                self.config['adjust_top'],
                                                self.config['adjust_right'],
                                                self.config['adjust_bottom'],
                                                self.config['adjust_left'])

        # Set wrapper widget attribute values
        self.z = self.config.get('z', 0)

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

        if 'color' in self.config and not isinstance(self.config['color'], RGBAColor):
            self.config['color'] = RGBAColor(self.config['color'])

        # Has to be after we set the attributes since it could be in the config
        self.key = key

        # Build animations
        if 'animations' in self.config and self.config['animations']:
            for k, v in self.config['animations'].items():
                if k == 'add_to_slide':
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

        self.expire = self.config['expire']
        if self.expire:
            self.schedule_removal(float(self.expire))

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} WidgetWrapper id={}>'.format(self.widget_type_name, self.id)

    def __lt__(self, other: "Widget") -> bool:
        """
        Less than comparison operator (based on z-order value). Used to 
        maintain proper z-order when adding widgets to a parent.
        Args:
            other: The widget to compare to this one.

        Returns:
            True if the other widget is less than the current widget (uses
            z-order to perform the comparison).
        """
        if hasattr(other, 'z'):
            return other.z < self.z
        else:
            return 0 < self.z

    def _create_child_widget(self) -> "Widget":
        raise NotImplementedError('_create_child_widget must be overriden in derived class')

    def _bind_child_widget_properties(self, widget: "Widget"):
        raise NotImplementedError('_bind_child_widget_properties must be overriden in derived class')

    def find_widgets_by_key(self, key: str) -> List["WidgetWrapper"]:
        """Return a list of widgets with the matching key value by searching
        the tree of children belonging to this widget."""
        return [x for x in self.walk(restrict=True, loopback=False) if hasattr(x, 'key') and x.key == key]

    def on_parent(self, instance, parent: "Widget") -> None:
        """Set the widget position based on various settings."""
        del instance
        if parent:
            self.size = parent.size
            # some attributes can be expressed in percentages. This dict holds
            # those, key is attribute name, val is max value
            self._percent_prop_dicts = dict(x=parent.width,
                                            y=parent.height,
                                            width=parent.width,
                                            height=parent.height,
                                            opacity=1,
                                            line_height=1)

            self.widget.pos = self.calculate_initial_position(parent.width,
                                                              parent.height,
                                                              self.config['x'],
                                                              self.config['y'])

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-statements
    @staticmethod
    def calculate_initial_position(parent_w: int, parent_h: int,
                                   x: Optional[Union[int, str]] = None,
                                   y: Optional[Union[int, str]] = None) -> tuple:
        """Returns the x,y position for the anchor of a widget within a larger 
        parent frame based on several positioning parameters.

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

        Returns: Tuple of x, y coordinates for the lower-left corner of the
            widget you're placing.

        See the widgets documentation for examples.

        """
        # Set defaults
        if x is None:
            x = 'center'
        if y is None:
            y = 'middle'

        # ----------------------
        # X / width / horizontal
        # ----------------------

        # Set position
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

        # --------------------
        # Y / height / vertical
        # --------------------

        # Set position
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

        return x, y

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-statements
    @staticmethod
    def calculate_anchor_offset(width: int,
                                height: int,
                                anchor_x: Optional[str] = None,
                                anchor_y: Optional[str] = None,
                                adjust_top: Optional[int] = None,
                                adjust_right: Optional[int] = None,
                                adjust_bottom: Optional[int] = None,
                                adjust_left: Optional[int] = None) -> tuple:
        """Returns the x,y position for the lower-left corner of a widget
        within a larger parent frame based on several positioning parameters.

        Args:
            width: Width of the element you're placing.
            height: Height of the element you're placing.
            anchor_x: (Optional) Which edge of the widget will be used for
                positioning. ('left', 'center' (or 'middle'), or 'right'. If None,
                'center' will be used.
            anchor_y: (Optional) Which edge of the widget will be used for
                positioning. ('top', 'middle' (or 'center'), or 'bottom'. If None,
                'center' will be used.
            adjust_top: (Optional) Moves the "top" of this widget down, meaning any
                positioning that includes calculations involving the top (anchor_y
                of 'top' or 'middle') use the alternate top position. Positive
                values move the top towards the center of the widget, negative
                values move it away. Negative values can be used to give the
                widget "space" on the top, and positive values can be used to
                remove unwanted space from the top of the widget. Note that this
                setting does not actually crop or cut off the top of the widget,
                rather, it just adjusts how the positioning is calculated.
            adjust_right: (Optional) adjusts the position calculations for the
                right side of the widget. Positive values move the right position
                towards the center, negative values move it away from the center.
            adjust_bottom: (Optional) adjusts the position calculations for the
                bottom of the widget. Positive values move the bottom position
                towards the center, negative values move it away from the center.
            adjust_left: (Optional) adjusts the position calculations for the
                left side of the widget. Positive values move the left position
                towards the center, negative values move it away from the center.

        Returns: Tuple of x, y coordinates for the lower-left corner of the
            widget you're placing.

        See the widgets documentation for examples.

        """
        # Set defaults
        offset_x = 0
        offset_y = 0
        if not anchor_x:
            anchor_x = 'center'
        if not anchor_y:
            anchor_y = 'middle'
        if not adjust_top:
            adjust_top = 0
        if not adjust_right:
            adjust_right = 0
        if not adjust_bottom:
            adjust_bottom = 0
        if not adjust_left:
            adjust_left = 0

        # ----------------------
        # X / width / horizontal
        # ----------------------

        # Adjust for anchor_x & adjust_right/left
        if anchor_x in ('center', 'middle'):
            offset_x -= (width - adjust_right + adjust_left) / 2
        elif anchor_x == 'right':
            offset_x -= width - adjust_right
        else:  # left
            offset_x -= adjust_left

        # --------------------
        # Y / height / vertical
        # --------------------

        # Adjust for anchor_y & adjust_top/bottom
        if anchor_y in ('middle', 'center'):
            offset_y -= (height - adjust_top + adjust_bottom) / 2
        elif anchor_y == 'top':
            offset_y -= height - adjust_top
        else:  # bottom
            offset_y -= adjust_bottom

        return offset_x, offset_y

    def on_widget_size(self, instance, size):
        del instance

        self.pos = self.calculate_anchor_offset(size[0], size[1],
                                                self.config['anchor_x'],
                                                self.config['anchor_y'],
                                                self.config['adjust_top'],
                                                self.config['adjust_right'],
                                                self.config['adjust_bottom'],
                                                self.config['adjust_left'])

    def _set_default_style(self) -> None:
        """Sets the default widget style name."""
        if ('{}_default'.format(self.widget_type_name.lower()) in
                self.mc.machine_config['widget_styles']):
            self._default_style = self.mc.machine_config['widget_styles'][
                '{}_default'.format(self.widget_type_name.lower())]

    def _apply_style(self, force_default: bool=False) -> None:
        """Apply any style to the widget that is specified in the config."""
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

    def prepare_for_removal(self) -> None:
        """Prepare the widget to be removed."""
        self.mc.clock.unschedule(self.remove)
        self._remove_animation_events()

    def schedule_removal(self, secs: float) -> None:
        """Schedule the widget to be removed after the specified number
        of seconds have elapsed."""
        self.mc.clock.schedule_once(self.remove, secs)

    def remove(self, *dt) -> None:
        """Perform the actual removal of the widget."""
        del dt

        try:
            self.parent.remove_widget(self)
        except AttributeError:
            pass

        self.on_remove_from_slide()

    def build_animation_from_config(self, config_list: list) -> Animation:
        """Build animation object from config."""
        if not isinstance(config_list, list):
            raise TypeError('build_animation_from_config requires a list')

        if self._widget is None:
            raise RuntimeError('build_animation_from_config must have a widget to animate')

        # find any named animations and replace them with the real ones
        animation_list = list()

        for entry in config_list:
            if 'named_animation' in entry:
                for named_anim_settings in (
                        self.mc.animations[entry['named_animation']]):
                    animation_list.append(named_anim_settings)
            else:
                animation_list.append(entry)

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
                if isinstance(getattr(self._widget, prop), list):
                    values_needed[prop] = len(getattr(self._widget, prop))
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

            for prop in settings['property']:
                if prop not in self.animation_properties:
                    self.mc.log.warning("%s widgets do not support animation "
                                        "for the %s property (animation will be ignored)",
                                        self.widget_type_name, prop)
                    continue

                if values_needed[prop] > 1:
                    val = [float(x) for x in values[:values_needed[prop]]]
                    del values[:values_needed[prop]]
                else:
                    val = values[0]
                    del values[0]
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
                    self._pre_animated_settings[prop] = getattr(self._widget, prop)

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
            self.animation.stop(self._widget)
        except AttributeError:
            pass

    def reset_animations(self, **kwargs) -> None:
        """Reset the widget properties back to their pre-animated values."""
        del kwargs
        for k, v in self._pre_animated_settings.items():
            setattr(self._widget, k, v)

    def _register_animation_events(self, event_name: str) -> None:
        """Register handlers for the various events that trigger animation actions."""
        self._animation_event_keys.add(self.mc.events.add_handler(
            event=event_name, handler=self.start_animation_from_event,
            event_name=event_name))

    def start_animation_from_event(self, event_name: str, **kwargs) -> None:
        """Starts an animation based on an event name that has previously
        been registered."""
        del kwargs

        if event_name not in self.config['animations']:
            return

        self.stop_animation()
        self.animation = self.build_animation_from_config(
            self.config['animations'][event_name])
        self.animation.start(self._widget)

    def _remove_animation_events(self) -> None:
        """Remove previously registered handlers for the various events that 
        trigger animation actions."""
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

        self.start_animation_from_event('add_to_slide')

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

    #
    # Properties
    #

    key = StringProperty(None, allownone=True)
    '''Widget keys are used to uniquely identify instances of widgets which you can later 
    use to update or remove the widget.
    '''

    z = NumericProperty(0)
    '''Z position (z-order) of the widget (used to determine the drawing order of widgets).
    '''

    def _get_widget(self):
        return self._widget

    widget = AliasProperty(_get_widget, None)
    '''Widget contains the widget that is wrapped/managed by this wrapper object.
    '''
