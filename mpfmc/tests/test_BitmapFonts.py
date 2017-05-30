from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestBitmapFonts(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/bitmap_fonts'

    def get_config_file(self):
        return 'test_bitmap_fonts.yaml'

    def test_loading_asset(self):
        # test that the bitmap_fonts asset class gets built correctly
        self.assertTrue(hasattr(self.mc, 'bitmap_fonts'))

        # /bitmap_fonts folder
        self.assertIn('f1fuv', self.mc.bitmap_fonts)
        test_font = self.mc.bitmap_fonts['f1fuv']
        self.assertIsNotNone(test_font)
        self.assertIsNotNone(test_font.bitmap_font)

        # Test the font descriptor list calculations
        self.assertEqual(test_font.bitmap_font.scale_w, 801)
        self.assertEqual(test_font.bitmap_font.scale_h, 300)
        self.assertEqual(test_font.bitmap_font.line_height, 50)
        self.assertEqual(test_font.bitmap_font.base, 50)

        self.assertTrue(len(test_font.bitmap_font.get_characters()), 95)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].id, 57)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].rect["w"], 50)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].rect["h"], 50)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].xadvance, 50)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].xoffset, 0)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].yoffset, 0)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].rect["x"], 450)
        self.assertEqual(test_font.bitmap_font.get_characters()['9'].rect["y"], 50)

        self.assertEqual(test_font.bitmap_font.get_characters()['Z'].rect["x"], 500)
        self.assertEqual(test_font.bitmap_font.get_characters()['Z'].rect["y"], 150)

        self.assertEqual(test_font.bitmap_font.get_characters()['z'].rect["x"], 500)
        self.assertEqual(test_font.bitmap_font.get_characters()['z'].rect["y"], 250)

        # Test the extent calculations
        self.assertEqual(test_font.bitmap_font.get_extents("testing"), (350, 50))
        self.assertEqual(test_font.bitmap_font.get_extents("more testing"), (600, 50))
        self.assertEqual(test_font.bitmap_font.get_ascent(), 50)
        self.assertEqual(test_font.bitmap_font.get_descent(), 0)

    def test_bitmap_font_text(self):
        # Very basic test
        self.mc.events.post('static_text')
        self.advance_real_time(3)

