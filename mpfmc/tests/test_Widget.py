from mpfmc.widgets.text import Text
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestWidget(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/widgets'

    def get_config_file(self):
        return 'test_widgets.yaml'

    def test_widget_loading_from_config(self):
        # check that all were loaded. First is a dict
        self.assertIn('widget1', self.mc.widgets)
        self.assertIs(type(self.mc.widgets['widget1']), list)

        # List with one item
        self.assertIn('widget2', self.mc.widgets)
        self.assertIs(type(self.mc.widgets['widget2']), list)

        # Lists with multiple items.
        self.assertIn('widget3', self.mc.widgets)
        self.assertIs(type(self.mc.widgets['widget3']), list)
        self.assertEqual(len(self.mc.widgets['widget3']), 3)

        # Ensure they're in order. Order is the order they're drawn,
        # so the highest priority one is last. We don't care about z values
        # at this point since those are threaded in when the widgets are
        # added to the slides, but we want to make sure that widgets of the
        # same z are in the order based on their order in the config file.
        self.assertEqual(self.mc.widgets['widget3'][0]['text'],
                         'widget3.3')
        self.assertEqual(self.mc.widgets['widget3'][1]['text'],
                         'widget3.2')
        self.assertEqual(self.mc.widgets['widget3'][2]['text'],
                         'widget3.1')

        # List with multiple items and custom z orders
        self.assertIn('widget4', self.mc.widgets)

    def test_adding_widgets_to_slide(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
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
        for widget, index in zip(
                self.mc.targets['default'].current_slide.children[0].children,
                target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

        # add widget 5 which is z order 200
        self.mc.targets['default'].current_slide.add_widgets_from_library(
                'widget5')

        # should be inserted between 4.1 and 4.5
        target_order = ['4.7', '4.6', '4.3', '4.4', '4.1', '5', '4.5', '4.2']
        for widget, index in zip(
                self.mc.targets['default'].current_slide.children[0].children,
                target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

    def test_widget_player_add_to_current_slide(self):
        # create a slide
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # post the event to add widget1 to the default target, default slide
        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # widget1 should be on the default slide
        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_player_add_to_named_slide(self):
        # create two slides
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # Add widget1 to slide 1
        self.mc.events.post('add_widget2_to_slide1')
        self.advance_time()

        # widget1 should be in slide1, not slide2, not current slide
        self.assertIn('widget2',
                      [x.text for x in
                       self.mc.active_slides['slide1'].children[0].children])
        self.assertNotIn('widget2',
                         [x.text for x in
                          self.mc.active_slides['slide2'].children[
                              0].children])
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # show slide1 and make sure the widget is there
        self.mc.targets['default'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_player_add_to_target(self):
        # create two slides
        self.mc.targets['display2'].add_slide(name='slide1')
        self.mc.targets['display2'].show_slide('slide1')
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide1')

        self.mc.targets['display2'].add_slide(name='slide2')
        self.mc.targets['display2'].show_slide('slide2')
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide2')

        # Add widget1 to slide 1
        self.mc.events.post('add_widget1_to_display2')
        self.advance_time()

        # widget1 should be in slide2, the current on display2. It should
        # not be in slide1
        self.assertIn('widget1',
                      [x.text for x in
                       self.mc.active_slides['slide2'].children[0].children])
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'display2'].current_slide.children[0].children])
        self.assertNotIn('widget1',
                         [x.text for x in
                          self.mc.active_slides['slide1'].children[
                              0].children])

        # show slide1 and make sure the widget is not there
        self.mc.targets['display2'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['display2'].current_slide_name,
                         'slide1')
        self.assertNotIn('widget1', [x.text for x in self.mc.targets[
            'display2'].current_slide.children[0].children])

    def test_removing_mode_widget_on_mode_stop(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 2
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget. This will also test that the
        # widget_player in a mode can add a widget from the base
        self.mc.events.post('mode1_add_widgets')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # stop the mode
        self.mc.modes['mode1'].stop()
        self.advance_time()

        # make sure the mode widget is gone, but the first one is still there
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widgets_in_slide_frame_parent(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 6
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # add widget 6, z: -100, so it should go to parent frame
        self.mc.events.post('add_widget6')
        self.advance_time()

        # verify widget1 is in the slide but not widget 6
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify widget6 is the highest priority in the parent frame
        # (highest priority is the last element in the list)
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent.children[0].text)

        # now switch the slide
        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # make sure neither widget is in this slide
        self.assertNotIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # make sure widget6 is still in the SlideFrameParent
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent.children[0].text)

    def test_widget_to_parent_via_widget_settings(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not box11
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('box11', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('box12', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # add boxx11, z: -1, so it should go to parent frame
        self.mc.events.post('widget_to_parent')
        self.advance_time()

        # verify widget1 is in the slide but not box11
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('box11', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('box12', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify widget6 is the highest priority in the parent frame
        # (highest priority is the last element in the list)
        self.assertEqual('box12', self.mc.targets[
            'default'].parent.children[-3].text)
        self.assertEqual('box11', self.mc.targets[
            'default'].parent.children[-2].text)

        self.advance_time(2)

    def test_removing_mode_widget_from_parent_frame_on_mode_stop(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 6
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget.
        self.mc.events.post('mode1_add_widget6')
        self.advance_time()

        # make sure the new widget is not in the slide, but the old one is
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify widget6 is the highest priority in the parent frame
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent.children[0].text)
        self.assertTrue(isinstance(self.mc.targets[
            'default'].parent.children[0], Text))

        # stop the mode
        self.mc.modes['mode1'].stop()
        self.advance_time()

        # make sure the the first one is still there
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify widget6 is gone
        self.assertFalse(isinstance(self.mc.targets[
            'default'].parent.children[-1], Text))

    def test_removing_widget(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # post the event to add widget1 to the default target, default slide
        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget2_to_current')
        self.advance_time()

        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        self.mc.events.post('remove_widget1')
        self.advance_time()

        self.assertNotIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_expire(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget7')
        self.advance_time()

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('_global-widget7', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('_global-widget7', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_player_expire(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget8_expire')
        self.advance_time()

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('_global-widget8', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('_global-widget8', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_player_custom_widget_settings(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget8_custom_settings')
        self.advance_time()

        w8 = [x for x in self.mc.targets[
              'default'].current_slide.children[0].children
              if x.key == '_global-widget8'][0]

        self.assertEqual([1, 0, 0, 1], w8.color)
        self.assertEqual(70, w8.font_size)

    def test_widget_removal_from_slide_player(self):
        # tests that we can remove a widget by key that was shown via the
        # slide player instead of the widget player
        self.mc.events.post('show_slide_1')
        self.advance_time()

        # make sure the two widgets are there
        self.assertIn('WIDGET WITH KEY', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('WIDGET NO KEY', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        self.mc.events.post('remove_widget1_by_key')
        self.advance_time()

        # make sure the one with key is gone but the other is there
        self.assertNotIn('WIDGET WITH KEY', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('WIDGET NO KEY', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_widget_expire_from_slide_player(self):
        # tests that we can remove a widget by key that was shown via the
        # slide player instead of the widget player
        self.mc.events.post('show_slide_1_with_expire')
        self.advance_time()

        # make sure the two widgets are there
        self.assertIn('WIDGET EXPIRE 1s', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('WIDGET NO EXPIRE', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        self.advance_time(1)

        # make sure the one with key is gone but the other is there
        self.assertNotIn('WIDGET EXPIRE 1s', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('WIDGET NO EXPIRE', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_opacity(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget8_opacity_50')
        self.advance_time()

        w8 = [x for x in self.mc.targets[
              'default'].current_slide.children[0].children
              if x.key == '_global-widget8'][0]

        self.assertEqual(.5, w8.opacity)

    def test_updating_widget_settings(self):
        self.mc.events.post('show_slide_2')
        self.advance_time()

        self.mc.events.post('event_a')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.get_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'A')
        self.assertEqual(widget.color, [1.0, 0.0, 0.0, 1.0])

        self.mc.events.post('event_s')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.get_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'S')
        self.assertEqual(widget.color, [0.0, 1.0, 0.0, 1.0])

        self.mc.events.post('event_d')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.get_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'D')
        self.assertEqual(widget.color, [0.0, 0.0, 1.0, 1.0])

    def test_widget_updating(self):
        self.mc.events.post('show_slide_3')
        self.advance_time(1)

        self.mc.events.post('widget_4up')
        self.advance_time(1)

        self.mc.events.post('widget_4up_red')
        self.advance_time(1)

    def test_widget_player_errors(self):
        pass
        # no slide
        # bad target
        # todo

    # todo test non named widgets?
