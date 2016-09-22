from mpfmc.uix.slide_frame import SlideFrame
from mpfmc.uix.widget import MpfWidget
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

        # Ensure they're in order. Order is the order they're drawn. We don't
        # care about z values at this point since those are threaded in when
        # the widgets are added to the slides, but we want to make sure that
        # widgets of the same z are in the order based on their order in the
        # config file.
        self.assertEqual(self.mc.widgets['widget3'][0]['text'],
                         'widget3.1')
        self.assertEqual(self.mc.widgets['widget3'][1]['text'],
                         'widget3.2')
        self.assertEqual(self.mc.widgets['widget3'][2]['text'],
                         'widget3.3')

        # List with multiple items and custom z orders
        self.assertIn('widget4', self.mc.widgets)

    def test_widget_z_order_from_named_widget(self):
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
        # config.

        target_order = ['4.2', '4.5', '4.1', '4.4', '4.3', '4.6', '4.7']
        for widget, index in zip(
                self.mc.targets['default'].current_slide.children[0].children,
                target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

        # add widget 5 which is z order 200
        self.mc.targets['default'].current_slide.add_widgets_from_library(
                'widget5')

        # should be inserted between 4.5 and 4.1
        target_order = ['4.2', '4.5', '5', '4.1', '4.4', '4.3', '4.6', '4.7']
        for widget, index in zip(
                self.mc.targets['default'].current_slide.children[0].children,
                target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

    def test_widget_z_order_from_slide_player(self):
        self.mc.events.post('show_slide_with_widgets')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide_1')

        # initial order & z orders from config
        # 4.1 / 1
        # 4.2 / 1000
        # 4.3 / None
        # 4.4 / 1
        # 4.5 / 1000
        # 4.6 / None
        # 4.7 / None

        # Order should be by z order (highest first), then by order in the
        # config.

        target_order = ['4.2', '4.5', '4.1', '4.4', '4.3', '4.6', '4.7']
        for widget, index in zip(
                self.mc.targets['default'].current_slide.children[0].children,
                target_order):
            self.assertEqual(widget.text, 'widget{}'.format(index))

    def test_widget_z_order_from_named_slide(self):
        self.mc.events.post('show_slide_with_lots_of_widgets')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide_with_lots_of_widgets')

        # initial order & z orders from config
        # 4.1 / 1
        # 4.2 / 1000
        # 4.3 / None
        # 4.4 / 1
        # 4.5 / 1000
        # 4.6 / None
        # 4.7 / None

        # Order should be by z order (highest first), then by order in the
        # config.

        target_order = ['4.2', '4.5', '4.1', '4.4', '4.3', '4.6', '4.7']
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
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # Add widget2 to slide 1
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

    def test_widget_player_add_to_invalid_slide(self):
        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        self.mc.events.post('add_widget2_to_slide1')

        with self.assertRaises(KeyError):
            self.advance_time()

    def test_widget_player_with_different_key_than_named_widget(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # widget_player for show_widget9 specifies widget9 with a key
        # "widget9_wp_key", but widget9 in the widgets: section has a key
        # "widget9_key"

        self.mc.events.post('show_widget9')

        with self.assertRaises(KeyError,
                msg="Widget has incoming key 'wigdet9_wp_key' which does not "
                "match the key in the widget's config 'widget9_key'."):

            self.advance_time()

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

    def test_removing_mode_widget_with_custom_key_on_mode_stop(self):
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
        self.mc.events.post('mode1_add_widget_with_key')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # make sure the key of the new widget is correct
        widget2 = self.mc.targets[
            'default'].current_slide.children[0].children[1]
        self.assertEqual(widget2.text, 'widget2')
        self.assertEqual(widget2.key, 'newton_crosby')

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

        # add widget 6, target: default, so it should go in parent frame
        self.mc.events.post('add_widget6')
        self.advance_time()

        # verify widget1 is in the slide but not widget 6
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('widget6', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify widget6 is the highest priority in the parent frame
        # (highest priority is the first element in the list)
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

        # add box11 into parent and box12 into slide
        self.mc.events.post('widget_to_parent')
        self.advance_time()

        # verify widget1 and box12 are in the slide but not box11
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('box11', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('box12', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # verify box11 is in the parent frame
        self.assertTrue(isinstance(self.mc.targets[
            'default'].current_slide.parent.parent.children[0], MpfWidget))
        self.assertTrue(isinstance(self.mc.targets[
            'default'].current_slide.parent, SlideFrame))

        self.assertEqual('box11', self.mc.targets[
            'default'].current_slide.parent.parent.children[0].text)

        # switch the slide
        self.mc.events.post('show_new_slide')
        self.advance_time()
        self.assertEqual('box11', self.mc.targets[
            'default'].current_slide.parent.parent.children[0].text)
        self.assertEqual('NEW SLIDE', self.mc.targets[
            'default'].current_slide.stencil.children[0].text)

        # make sure positioning works
        self.assertEqual(0, self.mc.targets[
            'default'].current_slide.stencil.children[0].y)

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

        # post the event to add the widget to the parent frame
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

    def test_widget_player_expire_in_parent_frame(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget8_expire_parent')
        self.advance_time()

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('_global-widget8', [x.key for x in self.mc.targets[
            'default'].parent.parent.children[0].children])

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.key for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertNotIn('_global-widget8', [x.key for x in self.mc.targets[
            'default'].parent.parent.children[0].children])

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
        self.advance_time()

        self.mc.events.post('widget_4up')
        self.advance_time()

        self.mc.events.post('widget_4up_red')
        self.advance_time()

    def test_widget_with_key(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # should be there
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # should no longer be there
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should be there (automagically)
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should be there (still)
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # should no longer be there
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should not appear
        self.assertNotIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

    def test_updating_mode_widget_by_key(self):
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
        self.mc.events.post('mode1_add_widget_with_key')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
        self.assertIn('widget2', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])

        # make sure the key of the new widget is correct
        widget2 = self.mc.targets[
            'default'].current_slide.children[0].children[1]
        self.assertEqual(widget2.text, 'widget2')
        self.assertEqual(widget2.key, 'newton_crosby')

        # update widget2 by key
        self.mc.events.post('mode1_update_widget2')
        self.advance_time()

        widget2 = self.mc.targets[
            'default'].current_slide.children[0].children[1]
        self.assertEqual(widget2.text, 'UPDATED TEXT')
        self.assertEqual(widget2.key, 'newton_crosby')

    def test_widget_player_with_placeholder(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.mc.events.post('show_widget10', text="asd")
        self.advance_time()

        # verify asd is there
        self.assertIn('asd', [x.text for x in self.mc.targets[
            'default'].current_slide.children[0].children])
