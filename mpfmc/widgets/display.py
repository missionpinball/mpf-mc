from typing import Optional, TYPE_CHECKING

from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.effectwidget import EffectWidget
from kivy.clock import Clock

from mpfmc.uix.widget import MpfWidget
from mpfmc.uix.display import DisplayOutput

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc
    from mpfmc.uix.slide import Slide


class DisplayWidget(MpfWidget, RelativeLayout):
    widget_type_name = 'Display'
    animation_properties = ('x', 'y')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None,
                 **kwargs: dict) -> None:
        del kwargs

        super().__init__(mc=mc, config=config, key=key)

        self.size = (self.config['width'], self.config['height'])
        self.display = self.mc.displays[self.config['source_display']]
        self.effects = EffectWidget(size=self.size)

        if 'effects' in self.config:
            self._add_effects(self.config['effects'])

        # Establish link between display and this display widget
        self.add_widget(self.effects)
        self.display_output = DisplayOutput(self.effects, self.display)
        Clock.schedule_once(self._set_initial_position, -1)

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<DisplayWidget size={}, source={}>'.format(
                    self.size, self.display.name)
        except AttributeError:
            return '<DisplayWidget size={}, source=(none)>'.format(
                    self.size)

    def _set_initial_position(self, dt) -> None:
        del dt
        try:
            self.pos = self.calculate_position(self.parent.width, self.parent.height,
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

    def _add_effects(self, config: Optional[list]) -> None:
        """Adds any effects specified in the config for this display widget."""
        if config:
            effects_list = list()
            for effect_config in config:
                effect_config['width'] = self.width
                effect_config['height'] = self.height
                effects_list.extend(self.mc.effects_manager.get_effect(effect_config))

            self.effects.effects = effects_list

    @property
    def current_slide(self) -> Optional["Slide"]:
        """The current slide shown on the linked display."""
        if self.display:
            return self.display.current_slide
        else:
            return None

    @property
    def current_slide_name(self) -> Optional[str]:
        """The name of the current slide shown on the linked display."""
        if self.display:
            return self.display.current_slide_name
        else:
            return None


widget_classes = [DisplayWidget]
