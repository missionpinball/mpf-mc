"""A widgets showing a camera image."""
from kivy.uix.camera import Camera
from mpfmc.uix.widget import Widget


class CameraWidget(Widget, Camera):

    """A widgets showing a camera image."""

    widget_type_name = "Camera"

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

    def pass_to_kivy_widget_init(self):
        return dict(resolution=(self.config['width'],
                                self.config['height']),
                    index=self.config['camera_index'])


widget_classes = [CameraWidget]
