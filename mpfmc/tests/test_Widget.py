"""Test widgets."""
import weakref

import gc

from mpfmc.uix.widget import WidgetContainer, Widget
from mpfmc.widgets.rectangle import Rectangle
from mpfmc.widgets.text import Text
from mpfmc.widgets.bezier import Bezier
from mpfmc.widgets.line import Line
from mpfmc.widgets.ellipse import Ellipse
from mpfmc.widgets.quad import Quad
from mpfmc.widgets.point import Point
from mpfmc.widgets.triangle import Triangle
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock


class TestWidgetWithNamedColor(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/widgets'

    def get_config_file(self):
        return 'test_widgets_with_named_colors.yaml'

    def test_named_colors(self):
        self.mc.events.post("add_widget1_to_current")
        self.advance_real_time()

class TestWidget(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/widgets'

    def get_config_file(self):
        return 'test_widgets.yaml'

    def test_anchor_offset_position(self):
        # For all these tests, the widget is 10x10

        # No anchor set, widget should be centered in the parent. Parent is
        # 100x100, widget is 10x10, so center of the parent is 50, 50, and
        # lower left corner of the widget is 45, 45

        # test with all defaults
        config = {"width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')

        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.size, [10, 10])
        self.assertEqual(widget.anchor_offset_pos, (-5, -5))

        # test anchors

        # bottom left
        config = {"anchor_x": "left", "anchor_y": "bottom",
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')

        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (0, 0))

        # add adjustments
        config = {"anchor_x": "left", "anchor_y": "bottom", "adjust_top": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (0, 0))

        config = {"anchor_x": "left", "anchor_y": "bottom", "adjust_right": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (0, 0))

        config = {"anchor_x": "left", "anchor_y": "bottom", "adjust_bottom": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (0, -2))

        config = {"anchor_x": "left", "anchor_y": "bottom", "adjust_left": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-2, 0))

        # middle middle
        config = {"anchor_x": "middle", "anchor_y": "middle",
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -5))

        # add adjustments
        config = {"anchor_x": "middle", "anchor_y": "middle", "adjust_top": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -4))

        config = {"anchor_x": "middle", "anchor_y": "middle", "adjust_right": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-4, -5))

        config = {"anchor_x": "middle", "anchor_y": "middle", "adjust_bottom": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -6))

        config = {"anchor_x": "middle", "anchor_y": "middle", "adjust_left": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-6, -5))

        # center center
        config = {"anchor_x": "center", "anchor_y": "center",
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -5))

        # add adjustments
        config = {"anchor_x": "center", "anchor_y": "center", "adjust_top": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -4))

        config = {"anchor_x": "center", "anchor_y": "center", "adjust_right": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-4, -5))

        config = {"anchor_x": "center", "anchor_y": "center", "adjust_bottom": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-5, -6))

        config = {"anchor_x": "center", "anchor_y": "center", "adjust_left": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-6, -5))

        # top right
        config = {"anchor_x": "right", "anchor_y": "top",
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')

        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-10, -10))

        # add adjustments
        config = {"anchor_x": "right", "anchor_y": "top", "adjust_top": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-10, -8))

        config = {"anchor_x": "right", "anchor_y": "top", "adjust_right": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-8, -10))

        config = {"anchor_x": "right", "anchor_y": "top", "adjust_bottom": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-10, -10))

        config = {"anchor_x": "right", "anchor_y": "top", "adjust_left": 2,
                  "width": 10, "height": 10, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        self.assertEqual(widget.anchor_offset_pos, (-10, -10))

    def test_on_container_parent(self):
        parent = self.mc.targets['default'].add_slide(name='parent')

        # test without rounding
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle"}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)

        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [400, 300])

        # test with offsetting down
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle",
                  "round_anchor_x": "left", "round_anchor_y": "bottom",}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [399.5, 299.5])

        # test with offsetting up
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle",
                  "round_anchor_x": "right", "round_anchor_y": "top",}
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [400.5, 300.5])

        # test with inheriting parent offsets
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle"}
        parent.display.config['round_anchor_x'] = "left"
        parent.display.config['round_anchor_y'] = "top"
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [399.5, 300.5])

        # test with widget config overriding parent offset
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle",
                  "round_anchor_x": "right", "round_anchor_y": "bottom"}
        parent.display.config['round_anchor_x'] = "left"
        parent.display.config['round_anchor_y'] = "top"
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [400.5, 299.5])

        # test with widget config removing parent offset
        config = {"anchor_x": "center", "anchor_y": "middle",
                  "width": 11, "height": 11, "type": "rectangle",
                  "round_anchor_x": "center", "round_anchor_y": "middle"}
        parent.display.config['round_anchor_x'] = "left"
        parent.display.config['round_anchor_y'] = "top"
        self.mc.config_validator.validate_config('widgets:rectangle', config, base_spec='widgets:common')
        widget = Rectangle(self.mc, config)
        widget.on_container_parent(None, parent)
        self.assertEqual(widget.pos, [400, 300])

    def test_calculate_initial_position(self):
        # Parent is
        # 100x100, so center of the parent is 50, 50

        # test with all defaults

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x=None, y=None)
        self.assertEqual((res_x, res_y), (50, 50))

        # test positive x, y numbers

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x=10, y=10)
        self.assertEqual((res_x, res_y), (10, 10))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x=33, y=66)
        self.assertEqual((res_x, res_y), (33, 66))

        # test negative x, y numbers

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x=-10, y=-10)
        self.assertEqual((res_x, res_y), (-10, -10))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x=-33, y=-66)
        self.assertEqual((res_x, res_y), (-33, -66))

        # test positive percentages

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="80%", y="20%")
        self.assertEqual((res_x, res_y), (80, 20))

        # test negative percentages (dunno how useful these are, but they work)

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="-80%", y="-20%")
        self.assertEqual((res_x, res_y), (-80, -20))

        # test positioning strings

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="center", y="center")
        self.assertEqual((res_x, res_y), (50, 50))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="center+10", y="center + 10")
        self.assertEqual((res_x, res_y), (60, 60))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="middle-10", y="middle - 10")
        self.assertEqual((res_x, res_y), (40, 40))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="left", y="bottom")
        self.assertEqual((res_x, res_y), (0, 0))

        res_x, res_y = Widget.calculate_initial_position(parent_h=100, parent_w=100,
                                                         x="right", y="top")
        self.assertEqual((res_x, res_y), (100, 100))

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

    def test_widget_reused_by_name(self):
        self.assertIn('widget_reusable', self.mc.widgets)

        # Named widgets can only be used in modes
        self.mc.modes['mode1'].start()
        self.mc.events.post('show_slide_with_named_widget')
        self.advance_time()
        current_slide = self.mc.targets['default'].current_slide

        self.assertEqual(self.mc.targets['default'].current_slide.name, 'slide_with_named_widget')
        self.assertIn("One Use Widget", [x.widget.text for x in current_slide.widgets])
        self.assertIn("Reusable Widget", [x.widget.text for x in current_slide.widgets])

    def test_widget_with_placeholder(self):
        self.assertIn('widget_placeholder_value1', self.mc.widgets)
        self.assertIn('widget_placeholder_value2', self.mc.widgets)
        self.mc.targets['default'].add_slide(name='blank_slide_one')
        self.mc.targets['default'].add_slide(name='blank_slide_two')
        self.mc.modes['mode1'].start()

        self.mc.targets['default'].show_slide('blank_slide_one')
        self.mc.events.post('show_widget_with_placeholder', value="value1")
        self.advance_time()
        self.assertEqual(["Placeholder widget", "Value One"],
                         [x.widget.text for x in self.mc.targets['default'].current_slide.widgets])

        self.mc.targets['default'].show_slide('blank_slide_two')
        self.mc.events.post('show_widget_with_placeholder', value="value2")
        self.advance_time()
        self.assertEqual(["Placeholder widget", "Value Two"],
                         [x.widget.text for x in self.mc.targets['default'].current_slide.widgets])

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
        for widget_container, index in zip(
                self.mc.targets['default'].current_slide.widgets,
                target_order):
            self.assertEqual(widget_container.widget.text, 'widget{}'.format(index))

        # add widget 5 which is z order 200
        self.mc.targets['default'].current_slide.add_widgets_from_library(
                'widget5')

        # should be inserted between 4.5 and 4.1
        target_order = ['4.2', '4.5', '5', '4.1', '4.4', '4.3', '4.6', '4.7']
        for widget_container, index in zip(
                self.mc.targets['default'].current_slide.widgets,
                target_order):
            self.assertEqual(widget_container.widget.text, 'widget{}'.format(index))

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
        for widget_container, index in zip(
                self.mc.targets['default'].current_slide.widgets,
                target_order):
            self.assertEqual(widget_container.widget.text, 'widget{}'.format(index))

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
        for widget_container, index in zip(
                self.mc.targets['default'].current_slide.widgets,
                target_order):
            self.assertEqual(widget_container.widget.text, 'widget{}'.format(index))

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
        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])

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

        # widget2 should be in slide1, not slide2, not current slide
        self.assertIn('widget2',
                      [x.widget.text for x in
                       self.mc.active_slides['slide1'].widgets])
        self.assertNotIn('widget2',
                         [x.widget.text for x in
                          self.mc.active_slides['slide2'].widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # Remove widget2
        self.mc.events.post('remove_widget2')
        self.advance_time()

        # widget2 should not be present in slide1
        self.assertNotIn('widget2',
                         [x.widget.text for x in
                          self.mc.active_slides['slide1'].widgets])

        # Update widget2 on slide1
        self.mc.events.post('update_widget2')
        self.advance_time()

        # widget2 should be in slide1, not slide2, not current slide
        self.assertIn('widget2',
                      [x.widget.text for x in
                       self.mc.active_slides['slide1'].widgets])
        self.assertNotIn('widget2',
                         [x.widget.text for x in
                          self.mc.active_slides['slide2'].widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # show slide1 and make sure the widget is there
        self.mc.targets['default'].current_slide_name = 'slide1'
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_widget_player_add_to_invalid_slide(self):
        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        self.mc.events.post('add_widget2_to_slide1')

        with self.assertRaises(Exception) as e:
            self.advance_time()
        self.assertIsInstance(e.exception.__cause__, KeyError)

    def test_widget_player_with_different_key_than_named_widget(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # widget_player for show_widget9 specifies widget9 with a key
        # "widget9_wp_key", but widget9 in the widgets: section has a key
        # "widget9_key"

        self.mc.events.post('show_widget9')

        with self.assertRaises(Exception) as e:
            self.advance_time()
        self.assertIsInstance(e.exception.__cause__, KeyError)
        self.assertEqual(str(e.exception.__cause__), "\"Widget has incoming key 'wigdet9_wp_key' which does not "
                                                     "match the key in the widget's config 'widget9_key'.\"")

    def test_removing_mode_widget_on_mode_stop(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 2
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget. This will also test that the
        # widget_player in a mode can add a widget from the base
        self.mc.events.post('mode1_add_widgets')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # stop the mode
        self.mc.modes['mode1'].stop()
        self.advance_time()

        # make sure the mode widget is gone, but the first one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_removing_mode_widget_with_custom_key_on_mode_stop(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 2
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget. This will also test that the
        # widget_player in a mode can add a widget from the base
        self.mc.events.post('mode1_add_widget_with_key')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # make sure the key of the new widget is correct
        widget2 = self.mc.targets[
            'default'].current_slide.widgets[1].widget
        self.assertEqual(widget2.text, 'widget2')
        self.assertEqual(widget2.key, 'newton_crosby')

        # stop the mode
        self.mc.modes['mode1'].stop()
        self.advance_time()

        # make sure the mode widget is gone, but the first one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_widgets_in_slide_frame_parent(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 6
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # add widget 6, z: -1, so it should go in slide parent
        self.mc.events.post('add_widget6')
        self.advance_time()

        # verify widget1 is in the slide but not widget 6
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # verify widget6 is the highest priority in the parent frame
        # (highest priority is the first element in the list)
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent_widgets[0].widget.text)

        # now switch the slide
        self.mc.targets['default'].add_slide(name='slide2')
        self.mc.targets['default'].show_slide('slide2')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # make sure neither widget is in this slide
        self.assertNotIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # make sure widget6 is still in the SlideFrameParent
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent_widgets[0].widget.text)

    def test_widget_to_parent_via_widget_settings(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not box11
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('box11', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('box12', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # add box11 into parent and box12 into slide
        self.mc.events.post('widget_to_parent')
        self.advance_time()

        # verify widget1 and box12 are in the slide but not box11
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('box11', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('box12', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # verify box11 is in the parent frame
        self.assertTrue(isinstance(self.mc.targets[
            'default'].parent_widgets[0], WidgetContainer))

        self.assertEqual('box11', self.mc.targets[
            'default'].parent_widgets[0].widget.text)

        # switch the slide
        self.mc.events.post('show_new_slide')
        self.advance_time()
        self.assertEqual('box11', self.mc.targets[
            'default'].parent_widgets[0].widget.text)
        self.assertEqual('NEW SLIDE', self.mc.targets[
            'default'].current_slide.widgets[0].widget.text)

        # make sure positioning works
        self.assertEqual(0, self.mc.targets[
            'default'].current_slide.widgets[0].widget.y)

    def test_removing_mode_widget_from_parent_frame_on_mode_stop(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 6
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget to the slide parent
        self.mc.events.post('mode1_add_widget6')
        self.advance_time()

        # make sure the new widget is not in the slide, but the old one is
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # verify widget6 is the highest priority in the parent frame
        self.assertEqual('widget6', self.mc.targets[
            'default'].parent_widgets[0].widget.text)
        self.assertTrue(isinstance(self.mc.targets[
            'default'].parent_widgets[0].widget, Text))

        # stop the mode
        self.mc.modes['mode1'].stop()
        self.advance_time()

        # make sure the the first one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # verify widget6 is gone
        self.assertNotIn('widget6', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.parent_widgets])

    def test_removing_widget(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # post the event to add widget1 to the default target, default slide
        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget2_to_current')
        self.advance_time()

        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        self.mc.events.post('remove_widget1')
        self.advance_time()

        self.assertNotIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_widget_expire(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget7')
        self.advance_time()
        widget7 = weakref.ref([x.widget for x in self.mc.targets['default'].current_slide.widgets
                               if x.widget.key == '_global-widget7'][0])
        self.assertTrue(widget7())

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('_global-widget7', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('_global-widget7', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])

        gc.collect()
        self.assertFalse(widget7())

    def test_widget_player_expire(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget8_expire')
        self.advance_time()

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('_global-widget8', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])

        widget8 = weakref.ref([x.widget for x in self.mc.targets['default'].current_slide.widgets
                               if x.widget.key == '_global-widget8'][0])
        self.assertTrue(widget8())

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('_global-widget8', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])

        gc.collect()
        self.assertFalse(widget8())

    def test_widget_player_expire_in_parent_frame(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget8_expire_parent')
        self.advance_time()

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('_global-widget8', [x.widget.key for x in self.mc.targets[
            'default'].parent_widgets])

        widget8 = weakref.ref(self.mc.targets[
            'default'].parent_widgets[0])
        self.assertTrue(widget8())

        self.advance_time(1)

        self.assertIn('_global-widget1', [x.widget.key for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('_global-widget8', [x.key for x in self.mc.targets[
            'default'].parent.walk()])

        gc.collect()
        self.assertFalse(widget8())

    def test_widget_player_custom_widget_settings(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget8_custom_settings')
        self.advance_time()

        w8 = [x.widget for x in self.mc.targets[
              'default'].current_slide.widgets
              if x.widget.key == '_global-widget8'][0]

        self.assertEqual([1, 0, 0, 1], w8.color)
        self.assertEqual(70, w8.font_size)
        self.assertAlmostEqual(-310, w8.anchor_offset_pos[0], delta=20)
        self.assertEqual(790, w8.x)  # anchor_x: right, x: right-10

    def test_widget_removal_from_slide_player(self):
        # tests that we can remove a widget by key that was shown via the
        # slide player instead of the widget player
        self.mc.events.post('show_slide_1')
        self.advance_time()

        # make sure the two widgets are there
        self.assertIn('WIDGET WITH KEY', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('WIDGET NO KEY', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        widget = weakref.ref([x.widget for x in self.mc.targets['default'].current_slide.widgets
                               if x.widget.text == 'WIDGET WITH KEY'][0])
        self.assertTrue(widget())

        self.mc.events.post('remove_widget1_by_key')
        self.advance_time()

        # make sure the one with key is gone but the other is there
        self.assertNotIn('WIDGET WITH KEY', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('WIDGET NO KEY', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        gc.collect()
        self.assertFalse(widget())

    def test_widget_expire_from_slide_player(self):
        # tests that we can remove a widget by key that was shown via the
        # slide player instead of the widget player
        self.mc.events.post('show_slide_1_with_expire')
        self.advance_time()

        # make sure the two widgets are there
        self.assertIn('WIDGET EXPIRE 1s', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('WIDGET NO EXPIRE', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        widget = weakref.ref([x.widget for x in self.mc.targets['default'].current_slide.widgets
                               if x.widget.text == 'WIDGET EXPIRE 1s'][0])
        self.assertTrue(widget())

        self.advance_time(1)

        # make sure the one with key is gone but the other is there
        self.assertNotIn('WIDGET EXPIRE 1s', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('WIDGET NO EXPIRE', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        gc.collect()
        self.assertFalse(widget())

    def test_opacity(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('add_widget8_opacity_50')
        self.advance_time()

        w8 = [x.widget for x in self.mc.targets['default'].current_slide.widgets
              if x.widget.key == '_global-widget8'][0]

        self.assertEqual(.5, w8.opacity)

    def test_updating_widget_settings(self):
        self.mc.events.post('show_slide_2')
        self.advance_time()

        self.mc.events.post('event_a')
        self.advance_time()

        widget = self.mc.targets['default'].current_slide.find_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'A')
        self.assertEqual(widget.color, [1.0, 0.0, 0.0, 1.0])

        self.mc.events.post('event_s')
        self.advance_time()

        old_widget = weakref.ref(widget)

        widget = self.mc.targets['default'].current_slide.find_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'S')
        self.assertEqual(widget.color, [0.0, 1.0, 0.0, 1.0])

        self.mc.events.post('event_d')
        self.advance_time()

        gc.collect()
        self.assertFalse(old_widget())

        old_widget = weakref.ref(widget)

        widget = self.mc.targets['default'].current_slide.find_widgets_by_key(
            '_global-widget1')[0]
        self.assertEqual(widget.text, 'D')
        self.assertEqual(widget.color, [0.0, 0.0, 1.0, 1.0])

        gc.collect()
        self.assertFalse(old_widget())

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
            'default'].current_slide.widgets])

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # should be there
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # should no longer be there
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should be there (automagically)
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should be there (still)
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # should no longer be there
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove slide
        self.mc.targets['default'].remove_slide('slide1')

        # post the event to add widget2 to slide1
        self.mc.events.post('show_christmas_slide_full')
        self.advance_time()

        # slide1 is not there. widget2 should also not be there
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # remove widget2 again
        self.mc.events.post('remove_christmas_full')
        self.advance_time()

        # show slide
        self.mc.targets['default'].show_slide('slide1')
        self.advance_time()

        # should not appear
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_updating_mode_widget_by_key(self):
        # create a slide and add some base widgets
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.mc.events.post('add_widget1_to_current')
        self.advance_time()

        # verify widget 1 is there but not widget 2
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertNotIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # start a mode
        self.mc.modes['mode1'].start()
        self.advance_time()

        # post the event to add the widget. This will also test that the
        # widget_player in a mode can add a widget from the base
        self.mc.events.post('mode1_add_widget_with_key')
        self.advance_time()

        # make sure the new widget is there, and the old one is still there
        self.assertIn('widget1', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('widget2', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

        # make sure the key of the new widget is correct
        widget2 = self.mc.targets[
            'default'].current_slide.widgets[1].widget
        self.assertEqual(widget2.text, 'widget2')
        self.assertEqual(widget2.key, 'newton_crosby')

        # update widget2 by key
        self.mc.events.post('mode1_update_widget2')
        self.advance_time()

        widget2 = self.mc.targets[
            'default'].current_slide.widgets[1].widget
        self.assertEqual(widget2.text, 'UPDATED TEXT')
        self.assertEqual(widget2.key, 'newton_crosby')

    def test_widget_player_with_placeholder(self):
        self.mc.targets['default'].add_slide(name='slide1')
        self.mc.targets['default'].show_slide('slide1')
        self.mc.events.post('show_widget10', text="asd")
        self.advance_time()

        # verify asd is there
        self.assertIn('asd', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_slide_frame_widget(self):
        self.mc.events.post("show_info_frame")
        self.advance_time(1)

    def test_properties_from_named_widget(self):
        self.mc.events.post('add_widget1_to_current')
        self.mc.events.post('add_widget2_to_current')
        self.advance_time()

        widget1 = self.mc.targets[
            'default'].current_slide.widgets[0].widget

        widget2 = self.mc.targets[
            'default'].current_slide.widgets[1].widget

        self.assertEqual(widget1.text, "widget1")
        self.assertEqual(widget2.text, "widget2")

        self.assertEqual(widget1.y, 360)
        self.assertEqual(widget2.y, 50)
        self.assertEqual(widget1.font_size, 100)
        self.assertEqual(widget2.font_size, 100)
        self.assertEqual(widget1.color, [1.0, 1.0, 0.0, 1])
        self.assertEqual(widget2.color, [1.0, 0.0, 0.0, 1])

    def test_animation_properties_from_widget_player(self):
        """Test multiple widget types with animations."""

        self.mc.events.post('show_text_widget')
        self.mc.events.post('show_bezier_widget')
        self.mc.events.post('show_rectangle_widget')
        self.mc.events.post('show_line_widget')
        self.mc.events.post('show_ellipse_widget')
        self.advance_real_time(1.5)

        self.mc.events.post('show_ellipse_widget')
        self.mc.events.post('show_quad_widget')
        self.mc.events.post('show_points_widget')
        self.mc.events.post('show_triangle_widget')
        self.advance_real_time(4.3)

        text_widget = self.mc.targets['default'].current_slide.widgets[0].widget
        self.assertIsInstance(text_widget, Text)
        self.assertEqual(text_widget.rotation, 45)
        self.assertEqual(text_widget.scale, 0.75)

        bezier_widget = self.mc.targets['default'].current_slide.widgets[1].widget
        self.assertIsInstance(bezier_widget, Bezier)
        self.assertEqual(bezier_widget.color, [1, 1, 0, 1])
        self.assertEqual(bezier_widget.rotation, -300)
        self.assertEqual(bezier_widget.points, [200, 200, 50, 100, 100, 250])

        rectangle_widget = self.mc.targets['default'].current_slide.widgets[2].widget
        self.assertIsInstance(rectangle_widget, Rectangle)
        self.assertEqual(rectangle_widget.rotation, 0)
        self.assertEqual(rectangle_widget.scale, 1)

        line_widget = self.mc.targets['default'].current_slide.widgets[3].widget
        self.assertIsInstance(line_widget, Line)
        self.assertEqual(line_widget.rotation, 360)
        self.assertEqual(line_widget.scale, 1.5)

        ellipse_widget = self.mc.targets['default'].current_slide.widgets[4].widget
        self.assertIsInstance(ellipse_widget, Ellipse)
        self.assertEqual(ellipse_widget.rotation, 360)
        self.assertEqual(ellipse_widget.pos, [500, 400])

        quad_widget = self.mc.targets['default'].current_slide.widgets[5].widget
        self.assertIsInstance(quad_widget, Quad)
        self.assertEqual(quad_widget.rotation, 0)
        self.assertEqual(quad_widget.scale, 1)
        self.assertEqual(quad_widget.points, [300, 100, 350, 200, 500, 150, 450, 50])

        points_widget = self.mc.targets['default'].current_slide.widgets[6].widget
        self.assertIsInstance(points_widget, Point)
        self.assertEqual(points_widget.rotation, 900)
        self.assertEqual(points_widget.scale, 1.5)
        self.assertEqual(points_widget.points, [100, 450, 100, 550, 200, 450])
        self.assertEqual(points_widget.pointsize, 8)

        triangle_widget = self.mc.targets['default'].current_slide.widgets[7].widget
        self.assertIsInstance(triangle_widget, Triangle)
        self.assertEqual(triangle_widget.rotation, -900)
        self.assertEqual(triangle_widget.scale, 1.5)
        self.assertEqual(triangle_widget.points, [100, 450, 100, 550, 200, 450])

    def test_events_when_removed(self):
        """Test events_when_removed property to ensure custom events are posted."""

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        self.mc.events.post('show_custom_events1_widget')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events1_added')

        self.mc.events.post('show_custom_events2_widget')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events2_added')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events2_added_again')

        self.mc.events.post('remove_custom_events1_widget')
        self.advance_real_time(0.1)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events1_removed')

        self.mc.events.post('remove_custom_events2_widget')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events2_removed')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='custom_events2_removed_again')

        self.mc.bcp_processor.send.reset_mock()
        self.mc.events.post('show_new_slide')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', name='text_on_new_slide2_added')

        self.mc.events.post('show_slide_1')
        self.mc.events.post('remove_new_slide')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', name='text_on_new_slide2_removed')


