from typing import Optional, TYPE_CHECKING

from kivy.uix.effectwidget import EffectWidget

from mpfmc.uix.widget_container import ContainedWidget
from mpfmc.uix.display import DisplayOutput

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc
    from mpfmc.uix.slide import Slide


class DisplayWidget(ContainedWidget):
    widget_type_name = 'Display'
    animation_properties = ('x', 'y')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        # The points in this widget are always relative to the bottom left corner
        self.anchor_pos = ("left", "bottom")

        self.display = self.mc.displays[self.config['source_display']]
        self.effects = EffectWidget(size=self.size)

        if 'effects' in self.config:
            self._add_effects(self.config['effects'])

        # Establish link between display and this display widget
        self.add_widget(self.effects)
        self.display_output = DisplayOutput(self.effects, self.display)

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<DisplayWidget size={}, source={}>'.format(
                    self.size, self.display.name)
        except AttributeError:
            return '<DisplayWidget size={}, source=(none)>'.format(
                    self.size)

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
