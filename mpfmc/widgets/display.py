from typing import Optional

from kivy.uix.effectwidget import EffectWidget

from kivy.uix.relativelayout import RelativeLayout

from mpfmc.uix.widget import Widget
from mpfmc.uix.display import DisplayOutput

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import
    from mpfmc.uix.slide import Slide   # pylint: disable-msg=cyclic-import,unused-import


class DisplayWidget(Widget, RelativeLayout):

    """A widget showing a display."""

    widget_type_name = 'Display'
    animation_properties = ('x', 'y', 'pos')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        self.display = mc.displays[config['source_display']]

        super().__init__(mc=mc, config=config, key=key)

        if 'effects' in self.config and self.config['effects']:
            self.effects = EffectWidget(pos=self.pos, size_hint=(1, 1))
            self.effects.key = None
            self._add_effects(self.config['effects'])
        else:
            self.effects = RelativeLayout(pos=self.pos, size_hint=(1, 1))

        # Establish link between display and this display widget
        self.display_output = DisplayOutput(self.effects, self.display)
        self.effects.add_widget(self.display_output)
        self.add_widget(self.effects)
        self.display_output.add_display_source(self.display)

    def prepare_for_removal(self):
        """Remove display and effects."""
        super().prepare_for_removal()
        self.remove_widget(self.effects)
        self.display_output.remove_display_source(self.display)

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<DisplayWidget size={}, pos={}, source={}>'.format(
                self.size, self.pos, self.display.name)
        except AttributeError:
            return '<DisplayWidget size={}, source=(none)>'.format(self.size)

    def on_pos(self, instance, pos):
        del instance
        self.effects.pos = pos

    def _add_effects(self, config: Optional[list]) -> None:
        """Adds any effects specified in the config for this display widget."""
        if config:
            effects_list = list()
            for effect_config in config:
                effect_config['width'] = self.width
                effect_config['height'] = self.height
                effects_list.extend(self.mc.effects_manager.get_effect(effect_config))

            self.effects.effects = effects_list

    def get_display(self):
        """List display."""
        return self.display

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
