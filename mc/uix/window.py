from kivy.core.window import Window as KivyWindow
from kivy.clock import Clock

class Window(object):

    @staticmethod
    def set_source_display(display):
        KivyWindow.clear()

        for widget in KivyWindow.children:
            KivyWindow.remove_widget(widget)


        KivyWindow.add_widget(display)

        KivyWindow.bind(system_size=display.on_window_resize)
        Clock.schedule_once(display.fit_to_window, -1)
