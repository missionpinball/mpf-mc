from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestBitmapFonts(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/bitmap_fonts'

    def get_config_file(self):
        return 'test_bitmap_fonts.yaml'

    def test_loading_asset(self):
        # test that the bitmap_fonts asset class gets built correctly
        self.assertTrue(hasattr(self.mc, 'bitmap_fonts'))

        # Monospaced font with simple descriptor list
        self.assertIn('F1fuv', self.mc.bitmap_fonts)
        f1fuv_font = self.mc.bitmap_fonts['F1fuv']
        self.assertIsNotNone(f1fuv_font)
        self.assertIsNotNone(f1fuv_font.bitmap_font)

        # Test the font descriptor list calculations
        self.assertEqual(f1fuv_font.bitmap_font.scale_w, 801)
        self.assertEqual(f1fuv_font.bitmap_font.scale_h, 300)
        self.assertEqual(f1fuv_font.bitmap_font.line_height, 50)
        self.assertEqual(f1fuv_font.bitmap_font.base, 50)

        self.assertTrue(len(f1fuv_font.bitmap_font.get_characters()), 95)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].id, 57)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].rect["w"], 50)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].rect["h"], 50)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].xadvance, 50)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].xoffset, 0)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].yoffset, 0)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].rect["x"], 450)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[57].rect["y"], 50)

        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[90].rect["x"], 500)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[90].rect["y"], 150)

        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[122].rect["x"], 500)
        self.assertEqual(f1fuv_font.bitmap_font.get_characters()[122].rect["y"], 250)

        # Test the extent calculations
        self.assertEqual(f1fuv_font.bitmap_font.get_extents("testing"), (350, 50))
        self.assertEqual(f1fuv_font.bitmap_font.get_extents("more testing"), (600, 50))
        self.assertEqual(f1fuv_font.bitmap_font.get_ascent(), 50)
        self.assertEqual(f1fuv_font.bitmap_font.get_descent(), 0)

        # Variable width font (with xml descriptor file)
        self.assertIn('test_font', self.mc.bitmap_fonts)
        test_font = self.mc.bitmap_fonts['test_font']
        self.assertIsNotNone(test_font)
        self.assertIsNotNone(test_font.bitmap_font)

        self.assertEqual(test_font.bitmap_font.scale_w, 361)
        self.assertEqual(test_font.bitmap_font.scale_h, 512)
        self.assertEqual(test_font.bitmap_font.line_height, 80)
        self.assertEqual(test_font.bitmap_font.base, 57)

        self.assertTrue(len(test_font.bitmap_font.get_characters()), 80)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].id, 122)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].rect["w"], 35)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].rect["h"], 39)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].xadvance, 36)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].xoffset, 1)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].yoffset, 19)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].rect["x"], 58)
        self.assertEqual(test_font.bitmap_font.get_characters()[122].rect["y"], 273)

        # Variable width font (with text descriptor file)
        self.assertIn('test_font_2', self.mc.bitmap_fonts)
        test_font_2 = self.mc.bitmap_fonts['test_font_2']
        self.assertIsNotNone(test_font_2)
        self.assertIsNotNone(test_font_2.bitmap_font)

        self.assertEqual(test_font_2.bitmap_font.scale_w, 330)
        self.assertEqual(test_font_2.bitmap_font.scale_h, 511)
        self.assertEqual(test_font_2.bitmap_font.line_height, 67)
        self.assertEqual(test_font_2.bitmap_font.base, 47)

        self.assertTrue(len(test_font_2.bitmap_font.get_characters()), 80)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].id, 122)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].rect["w"], 35)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].rect["h"], 39)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].xadvance, 30)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].xoffset, 1)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].yoffset, 16)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].rect["x"], 80)
        self.assertEqual(test_font_2.bitmap_font.get_characters()[122].rect["y"], 438)

    def test_bitmap_font_text(self):
        # Very basic test
        self.mc.events.post('static_text')
        self.advance_real_time(3)

