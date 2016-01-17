from mc.uix.slide import Slide
from .MpfMcTestCase import MpfMcTestCase


class TestWidget(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/widgets'

    def get_config_file(self):
        return 'test_widgets.yaml'

    def test_widget_loading_from_config(self):
        # check that all were loaded. First is a dict
        self.assertIn('widget1', self.mc.widget_configs)
        self.assertIs(type(self.mc.widget_configs['widget1']), list)

        # List with one item
        self.assertIn('widget2', self.mc.widget_configs)
        self.assertIs(type(self.mc.widget_configs['widget2']), list)

        # Lists with multiple items.
        self.assertIn('widget3', self.mc.widget_configs)
        self.assertIs(type(self.mc.widget_configs['widget3']), list)
        self.assertEqual(len(self.mc.widget_configs['widget3']), 3)

        # Ensure they're in order. Order is the order they're drawn,
        # so the highest priority one is last. We don't care about z values
        # at this point since those are threaded in when the widgets are
        # added to the slides, but we want to make sure that widgets of the
        # same z are in the order based on their order in the config file.
        self.assertEqual(self.mc.widget_configs['widget3'][0]['text'],
                         'widget3.3')
        self.assertEqual(self.mc.widget_configs['widget3'][1]['text'],
                         'widget3.2')
        self.assertEqual(self.mc.widget_configs['widget3'][2]['text'],
                         'widget3.1')

        # List with multiple items and custom z orders
        self.assertIn('widget4', self.mc.widget_configs)

    def test_adding_widgets_to_slide(self):
        self.mc.targets['default'].add_slide(name='slide1', config={})
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.targets['default'].current_slide.add_widgets_from_library(
                'widget4')

        # initial order & z orders from config
        # 4.1 / 1
        # 4.2 / 1000
        # 4.3 / None
        # 4.4 / 1
        # 4.5 / 1000
        # 4.6 / None
        # 4.7 / None

        # Order should be by z order (highest first), then by order in the
        # config. The entire list should be backwards, lowest, priority first.

        target_order = ['4.7', '4.6', '4.3', '4.4', '4.1', '4.5', '4.2']
        for widget, index in zip(self.mc.targets[
                                     'default'].current_slide.children,
                                 target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

        # add widget 5 which is z order 200
        self.mc.targets['default'].current_slide.add_widgets_from_library(
                'widget5')

        # should be inserted between 4.1 and 4.5
        target_order = ['4.7', '4.6', '4.3', '4.4', '4.1', '5', '4.5', '4.2']
        for widget, index in zip(self.mc.targets[
                                     'default'].current_slide.children,
                                 target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

    def test_widget_player_add_to_current_slide(self):
        # create a slide
        self.mc.targets['default'].add_slide(name='slide1', config={})
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # post the event to add widget1 to the default target, default slide
        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # A widget with text that reads 'widget1' should be on the default
        # slide
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children])

    def test_widget_player_add_to_named_slide(self):
        # create two slides
        self.mc.targets['default'].add_slide(name='slide1', config={})
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.targets['default'].add_slide(name='slide2', config={})
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # Add widget1 to slide 1
        self.mc.events.post('add_widget2_to_slide1')
        self.advance_time()

        # widget1 should be in slide1, not slide2, not current slide
        self.assertIn('widget1',
                      [x.text for x in Slide.active_slides['slide1'].children])
        self.assertNotIn('widget1',
                      [x.text for x in Slide.active_slides['slide2'].children])
        self.assertNotIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children])

        # show slide1 and make sure the widget is there
        self.mc.targets['default'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children])

    def test_widget_player_add_to_target(self):
        # create two slides
        self.mc.targets['display2'].add_slide(name='slide1', config={})
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide1')

        self.mc.targets['display2'].add_slide(name='slide2', config={})
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide2')

        # Add widget1 to slide 1
        self.mc.events.post('add_widget1_to_display2')
        self.advance_time()

        # widget1 should be in slide2, the current on display2. It should
        # not be in slide1
        self.assertIn('widget1',
                      [x.text for x in Slide.active_slides['slide2'].children])
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'display2'].current_slide.children])
        self.assertNotIn('widget1',
                      [x.text for x in Slide.active_slides['slide1'].children])


        # show slide1 and make sure the widget is not there
        self.mc.targets['display2'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide1')
        self.assertNotIn('widget1', [x.text for x in self.mc.targets[
            'display2'].current_slide.children])


# We don't have to test mode-based widget player settings since they just use
# the same ConfigPlayer base class which is tested in the slide tests.

    def test_widget_player_errors(self):
        pass

        # no slide
        # bad target
        #


        # test non named widgets?
