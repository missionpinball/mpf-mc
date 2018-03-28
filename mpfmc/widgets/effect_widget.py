"""Copy of kivy.uix.effectwidget.

Remove when https://github.com/kivy/kivy/pull/5679 is merged and released.
"""
from kivy.graphics.context_instructions import PushMatrix, Color, PopMatrix
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearBuffers, ClearColor
from kivy.graphics.instructions import RenderContext, Callback
from kivy.graphics.vertex_instructions import Rectangle
from kivy.uix.effectwidget import EffectFbo

from kivy.base import EventLoop
from kivy.properties import ListProperty, ObjectProperty

from kivy.uix.relativelayout import RelativeLayout


class EffectWidget(RelativeLayout):
    '''
    Widget with the ability to apply a series of graphical effects to
    its children. See the module documentation for more information on
    setting effects and creating your own.
    '''

    background_color = ListProperty((0, 0, 0, 0))
    '''This defines the background color to be used for the fbo in the
    EffectWidget.

    :attr:`background_color` is a :class:`ListProperty` defaults to
    (0, 0, 0, 0)
    '''

    texture = ObjectProperty(None)
    '''The output texture of the final :class:`~kivy.graphics.Fbo` after
    all effects have been applied.

    texture is an :class:`~kivy.properties.ObjectProperty` and defaults
    to None.
    '''

    effects = ListProperty([])
    '''List of all the effects to be applied. These should all be
    instances or subclasses of :class:`EffectBase`.

    effects is a :class:`ListProperty` and defaults to [].
    '''

    fbo_list = ListProperty([])
    '''(internal) List of all the fbos that are being used to apply
    the effects.

    fbo_list is a :class:`ListProperty` and defaults to [].
    '''

    _bound_effects = ListProperty([])
    '''(internal) List of effect classes that have been given an fbo to
    manage. This is necessary so that the fbo can be removed if the
    effect is no longer in use.

    _bound_effects is a :class:`ListProperty` and defaults to [].
    '''

    def __init__(self, **kwargs):
        # Make sure opengl context exists
        EventLoop.ensure_window()

        self.canvas = RenderContext(use_parent_projection=True,
                                    use_parent_modelview=True)
        self._callbacks = {}

        with self.canvas:
            self.fbo = Fbo(size=self.size)

        with self.fbo.before:   # noqa
            PushMatrix()
        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            self._background_color = Color(*self.background_color)
            self.fbo_rectangle = Rectangle(size=self.size)
        with self.fbo.after:    # noqa
            PopMatrix()

        super(EffectWidget, self).__init__(**kwargs)

        fbind = self.fbind
        fbo_setup = self.refresh_fbo_setup
        fbind('size', fbo_setup)
        fbind('effects', fbo_setup)
        fbind('background_color', self._refresh_background_color)

        self.refresh_fbo_setup()
        self._refresh_background_color()  # In case thi was changed in kwargs

    def _refresh_background_color(self, *args):     # noqa
        self._background_color.rgba = self.background_color

    def _propagate_updates(self, *largs):
        """Propagate updates from widgets."""
        del largs
        for fbo in self.fbo_list:
            fbo.ask_update()

    def refresh_fbo_setup(self, *args):     # noqa
        '''(internal) Creates and assigns one :class:`~kivy.graphics.Fbo`
        per effect, and makes sure all sizes etc. are correct and
        consistent.
        '''
        # Add/remove fbos until there is one per effect
        while len(self.fbo_list) < len(self.effects):
            with self.canvas:
                new_fbo = EffectFbo(size=self.size)
            with new_fbo:
                ClearColor(0, 0, 0, 0)
                ClearBuffers()
                Color(1, 1, 1, 1)
                new_fbo.texture_rectangle = Rectangle(size=self.size)

                new_fbo.texture_rectangle.size = self.size
            self.fbo_list.append(new_fbo)
        while len(self.fbo_list) > len(self.effects):
            old_fbo = self.fbo_list.pop()
            self.canvas.remove(old_fbo)

        # Remove fbos from unused effects
        for effect in self._bound_effects:
            if effect not in self.effects:
                effect.fbo = None
        self._bound_effects = self.effects

        # Do resizing etc.
        self.fbo.size = self.size
        self.fbo_rectangle.size = self.size
        for i in range(len(self.fbo_list)):
            self.fbo_list[i].size = self.size
            self.fbo_list[i].texture_rectangle.size = self.size

        # If there are no effects, just draw our main fbo
        if len(self.fbo_list) == 0:     # noqa
            self.texture = self.fbo.texture
            return

        for i in range(1, len(self.fbo_list)):
            fbo = self.fbo_list[i]
            fbo.texture_rectangle.texture = self.fbo_list[i - 1].texture

        # Build effect shaders
        for effect, fbo in zip(self.effects, self.fbo_list):
            effect.fbo = fbo

        self.fbo_list[0].texture_rectangle.texture = self.fbo.texture
        self.texture = self.fbo_list[-1].texture

        for fbo in self.fbo_list:
            fbo.draw()
        self.fbo.draw()

    def add_widget(self, widget):   # noqa
        # Add the widget to our Fbo instead of the normal canvas
        c = self.canvas
        self.canvas = self.fbo
        with widget.canvas:
            self._callbacks[widget.canvas] = Callback(self._propagate_updates)
        super(EffectWidget, self).add_widget(widget)
        self.canvas = c

    def remove_widget(self, widget):
        # Remove the widget from our Fbo instead of the normal canvas
        c = self.canvas
        widget.canvas.remove(self._callbacks[widget.canvas])
        del self._callbacks[widget.canvas]
        self.canvas = self.fbo
        super(EffectWidget, self).remove_widget(widget)
        self.canvas = c

    def clear_widgets(self, children=None):
        # Clear widgets from our Fbo instead of the normal canvas
        c = self.canvas
        self.canvas = self.fbo
        for canvas, callback in self._callbacks.items():
            canvas.remove(callback)
        self._callbacks = {}

        super(EffectWidget, self).clear_widgets(children)
        self.canvas = c
