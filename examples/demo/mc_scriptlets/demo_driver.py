from mc.core.scriptlet import Scriptlet


class DemoDriver(Scriptlet):

    def on_load(self):
        self.current_slide_index = 1
        self.total_slides = 5
        self.mc.demo_driver = self

        self.mc.events.add_handler('next_slide', self.next_slide)
        self.mc.events.add_handler('prev_slide', self.prev_slide)

    def next_slide(self):
        if self.current_slide_index == self.total_slides:
            return

        self.current_slide_index += 1
        self.mc.events.post('show_slide{}'.format(self.current_slide_index))

    def prev_slide(self):

        if self.current_slide_index == 1:
            return

        self.current_slide_index -= 1
        self.mc.events.post('show_slide{}'.format(self.current_slide_index))
