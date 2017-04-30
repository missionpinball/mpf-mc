from typing import List, Union, Optional, TYPE_CHECKING

from kivy.uix.widget import Widget, WidgetException
from kivy.uix.effectwidget import EffectWidget
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Scale

from mpfmc.uix.widget import MpfWidget

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class DisplayWidget(MpfWidget, Widget):
    widget_type_name = 'Display'

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None,
                 **kwargs: dict) -> None:
        del kwargs

        super().__init__(mc=mc, config=config, key=key)

        self.source = self.mc.displays[self.config['source_display']]
        self.effects = EffectWidget()

        if 'effects' in self.config:
            self._add_effects(self.config['effects'])

        try:
            self.effects.add_widget(self.source.parent)
        except WidgetException:
            self.source.parent.parent = None
            self.effects.add_widget(self.source.parent)

        self.effects.size = (self.config['width'], self.config['height'])

        self.effects.texture.mag_filter = 'nearest'
        self.effects.texture.min_filter = 'nearest'

        self.scale = min(self.width / self.source.width,
                         self.height / self.source.height)

        self.pos = (0, 0)

        # Apply scaling
        with self.canvas.before:
            PushMatrix()
            Scale(self.scale)

        with self.canvas.after:
            PopMatrix()

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<DMD size={}, source_size={}>'.format(
                    self.size, self.source.size)
        except AttributeError:
            return '<DMD size={}, source_size=(none)>'.format(
                    self.size)

    def on_pos(self, *args) -> None:
        self.pos = self.calculate_position(self.parent.width,
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

    def _add_effects(self, config: Optional[list]) -> None:
        if config:
            effects_list = list()
            for effect_config in config:
                effects_list.extend(self.mc.effects_manager.get_effect(effect_config))

            self.effects.effects = effects_list

widget_classes = [DisplayWidget]
