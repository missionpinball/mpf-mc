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
        self.assertIn('test_font', self.mc.bitmap_fonts)
        test_font = self.mc.bitmap_fonts['test_font']
        self.assertIsNotNone(test_font)
        self.assertIsNotNone(test_font._image)

        # Test the font descriptor list calculations
        self.assertEqual(test_font._common.scale_w, 801)
        self.assertEqual(test_font._common.scale_h, 300)
        self.assertEqual(test_font._common.line_height, 50)
        self.assertEqual(test_font._common.base, 50)

        self.assertTrue(len(test_font._characters), 95)
        self.assertEqual(test_font._characters['9'].char_id, 57)
        self.assertEqual(test_font._characters['9'].width, 50)
        self.assertEqual(test_font._characters['9'].height, 50)
        self.assertEqual(test_font._characters['9'].xadvance, 50)
        self.assertEqual(test_font._characters['9'].xoffset, 0)
        self.assertEqual(test_font._characters['9'].yoffset, 0)
        self.assertEqual(test_font._characters['9'].x, 450)
        self.assertEqual(test_font._characters['9'].y, 50)

        self.assertEqual(test_font._characters['Z'].x, 500)
        self.assertEqual(test_font._characters['Z'].y, 150)

        self.assertEqual(test_font._characters['z'].x, 500)
        self.assertEqual(test_font._characters['z'].y, 250)


