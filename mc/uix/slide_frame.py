from kivy.uix.screenmanager import ScreenManager

from mc.uix.slide import Slide


class SlideFrame(ScreenManager):
    def __init__(self, mc, name):
        super().__init__()
        self.mc = mc
        self.name = name

        mc.targets[name] = self

    @property
    def current_slide(self):
        """Returns the Slide object of the current slide."""
        return self.current_screen

    @current_slide.setter
    def current_slide(self, value):
        """Sets the current slide. You can set it to a Slide object or a
        string of the slide name."""
        if isinstance(value, Slide) and value in self.slides:
            self.current = value.name
        elif type(value) is str:
            self.current = value

    @property
    def current_slide_name(self):
        """Returns the string name of the current slide."""
        return self.current

    @current_slide_name.setter
    def current_slide_name(self, value):
        """Sets the current slide based on the string name of the slide you
        want to be shown."""
        self.current = value

    @property
    def slides(self):
        """List of slide objects of all the active slides for this slide
        frame."""
        return self.screens

    def add_slide(self, name, config, priority=0):
        Slide(mc=self.mc, name=name, target=self.name, config=config)

        if not self.current or priority >= self.current_screen.priority:
            self.current = name

    def add_widget(self, slide, show=True, force=False):
        super().add_widget(screen=slide)

        if force:
            self.current_slide = slide
        elif show and ((self.current_slide and slide.priority >=
            self.current_slide.priority) or not self.current_slide):
            self.current_slide = slide
