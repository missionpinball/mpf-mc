from mc.core.utils import set_position, get_insert_index
from tests.MpfMcTestCase import MpfMcTestCase


class TestUtils(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/utils'

    def get_config_file(self):
        return 'test_utils.yaml'

    def test_set_position(self):
        parent_w = 100
        parent_h = 100
        w = 10
        h = 10
        x = None
        y = None
        v_pos = None
        h_pos = None
        anchor_x = None
        anchor_y = None

        # No pos or anchor set, widget should be centered in the parent
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 45))

        x = 1
        y = None
        v_pos = None
        h_pos = None
        anchor_x = None
        anchor_y = None

        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (46, 45))


        h_pos = 'left'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (1, 45))

        h_pos = 'middle'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (46, 45))

        h_pos = 'center'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (46, 45))

        h_pos = 'right'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (91, 45))

        x = None
        y = 1
        v_pos = None
        h_pos = None
        anchor_x = None
        anchor_y = None

        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 46))

        v_pos = 'top'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 91))

        v_pos = 'middle'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 46))

        v_pos = 'center'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 46))

        v_pos = 'bottom'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 1))

        x = '80%'
        y = None
        v_pos = None
        h_pos = None
        anchor_x = None
        anchor_y = None

        h_pos = 'left'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (80, 45))

        h_pos = 'middle'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (35, 45))

        h_pos = 'center'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (35, 45))

        h_pos = 'right'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (10, 45))

        x = None
        y = '20%'
        v_pos = None
        h_pos = None
        anchor_x = None
        anchor_y = None

        v_pos = 'top' # 20% from the top, -5 for widget size offset
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 70))

        v_pos = 'middle'  # 20% from the middle, -5 for widget size offset
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 5))

        v_pos = 'center'  # 20% from the middle, -5 for widget size offset
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 5))

        v_pos = 'bottom'  # 20% from the bottom
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 20))

        x = None
        y = None
        v_pos = None
        h_pos = None

        anchor_x = 'left'
        anchor_y = 'bottom'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (50, 50))

        anchor_x = 'middle'
        anchor_y = 'middle'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 45))

        anchor_x = 'center'
        anchor_y = 'center'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (45, 45))

        anchor_x = 'right'
        anchor_y = 'top'
        res_x, res_y = set_position(parent_w, parent_h, w, h, x, y, h_pos,
                                    v_pos, anchor_x, anchor_y)
        self.assertEqual((res_x, res_y), (40, 40))

    def test_get_insert_index(self):
        self.mc.events.post('show_slide1')
        self.advance_time()

        index = get_insert_index(75, self.mc.targets['default'].current_slide)
        self.assertEqual(index, 2)
