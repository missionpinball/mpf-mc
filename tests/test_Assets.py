from tests.MpfMcTestCase import MpfMcTestCase


class TestAssets(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/assets'

    def get_config_file(self):
        return 'test_asset_loading.yaml'

    def test_machine_wide_asset_loading(self):

        # test that the images asset class gets built correctly
        self.assertTrue(self.mc, 'images')
        self.assertTrue(self.mc.asset_manager._asset_classes)
        self.assertEqual(self.mc.asset_manager._asset_classes[0]
                         ['path_string'], 'images')

        # tests that assets are registered as expected with various conditions

        # /images folder
        self.assertIn('image1', self.mc.images)  # .gif
        self.assertIn('image2', self.mc.images)  # .jpg
        self.assertIn('image3', self.mc.images)  # .png

        # test subfolders listed in assets:images machine-wide config folders
        self.assertIn('image4', self.mc.images)  # /images/preload
        self.assertIn('image5', self.mc.images)  # /images/on_demand


        # test images from subfolder not listed in assets:images
        self.assertIn('image11', self.mc.images)  # /images/custom1

        # test images from the images: section that have names configured to be
        # different from their file names
        self.assertIn('image_12_new_name', self.mc.images)  # image12.png
        # custom1/image13.png
        self.assertIn('image_13_new_name', self.mc.images)

        # test that the images that were renamed were not also loaded based on
        # their original names
        self.assertNotIn('image12', self.mc.images)
        self.assertNotIn('image13', self.mc.images)

        # test that config dicts are merged and/or overwritten properly

        # test custom k/v pair from default config based on the folder the
        # asset was in
        self.assertEqual(self.mc.images['image4'].config['test_key'],
                         'test_value')

        # test custom k/v pair from asset entry in the images: section
        self.assertEqual(self.mc.images['image3'].config['test_key'],
                         'test_value_override3')

        # same as above, but test that it also works when the asset name is
        # different from the file name
        self.assertEqual(self.mc.images['image_12_new_name'].config['test_key'],
                         'test_value_override12')

        # Test that mode assets were loaded properly
        self.assertIn('image6', self.mc.images)
        self.assertIn('image7', self.mc.images)
        self.assertIn('image8', self.mc.images)
        self.assertIn('image9', self.mc.images)
        self.assertIn('image10', self.mc.images)

        # Make sure all the assets are loaded. Wait if not
        while (self.mc.asset_manager.num_assets_to_load <
               self.mc.asset_manager.num_assets_loaded):
            self.advance_time()

        # Need to wait a bit since the loading was a separate thread
        self.advance_time(.1)

        # Make sure the ones that should have loaded on startup actually loaded
        self.assertTrue(self.mc.images['image1'].loaded)
        self.assertFalse(self.mc.images['image1'].loading)
        self.assertFalse(self.mc.images['image1'].unloading)

        self.assertTrue(self.mc.images['image2'].loaded)
        self.assertFalse(self.mc.images['image2'].loading)
        self.assertFalse(self.mc.images['image2'].unloading)

        self.assertTrue(self.mc.images['image3'].loaded)
        self.assertFalse(self.mc.images['image3'].loading)
        self.assertFalse(self.mc.images['image3'].unloading)

        self.assertTrue(self.mc.images['image8'].loaded)
        self.assertFalse(self.mc.images['image8'].loading)
        self.assertFalse(self.mc.images['image8'].unloading)

        self.assertTrue(self.mc.images['image2'].loaded)
        self.assertFalse(self.mc.images['image2'].loading)
        self.assertFalse(self.mc.images['image2'].unloading)

        self.assertTrue(self.mc.images['image4'].loaded)
        self.assertFalse(self.mc.images['image4'].loading)
        self.assertFalse(self.mc.images['image4'].unloading)

        self.assertTrue(self.mc.images['image7'].loaded)
        self.assertFalse(self.mc.images['image7'].loading)
        self.assertFalse(self.mc.images['image7'].unloading)

        self.assertTrue(self.mc.images['image11'].loaded)
        self.assertFalse(self.mc.images['image11'].loading)
        self.assertFalse(self.mc.images['image11'].unloading)

        self.assertTrue(self.mc.images['image_12_new_name'].loaded)
        self.assertFalse(self.mc.images['image_12_new_name'].loading)
        self.assertFalse(self.mc.images['image_12_new_name'].unloading)

        self.assertTrue(self.mc.images['image_13_new_name'].loaded)
        self.assertFalse(self.mc.images['image_13_new_name'].loading)
        self.assertFalse(self.mc.images['image_13_new_name'].unloading)

        # Make sure the ones that should not have loaded on startup didn't load
        self.assertFalse(self.mc.images['image5'].loaded)
        self.assertFalse(self.mc.images['image5'].loading)
        self.assertFalse(self.mc.images['image5'].unloading)

        self.assertFalse(self.mc.images['image9'].loaded)
        self.assertFalse(self.mc.images['image9'].loading)
        self.assertFalse(self.mc.images['image9'].unloading)

        self.assertFalse(self.mc.images['image10'].loaded)
        self.assertFalse(self.mc.images['image10'].loading)
        self.assertFalse(self.mc.images['image10'].unloading)

        # Start the mode and make sure those assets load
        self.mc.modes['mode1'].start()
        self.advance_time()

        # Give it a second to load. This file is tiny, so it shouldn't take
        # this long
        for x in range(10):
            if not self.mc.images['image9'].loaded:
                self.assertTrue(self.mc.images['image9'].loading)
                self.advance_time(.1)

        self.assertTrue(self.mc.images['image9'].loaded)
        self.assertFalse(self.mc.images['image9'].loading)
        self.assertFalse(self.mc.images['image9'].unloading)

        # test mode stop which should unload those assets
        self.mc.modes['mode1'].stop()

        for x in range(10):
            if self.mc.images['image9'].loaded:
                self.assertTrue(self.mc.images['image9'].unloading)
                self.advance_time(.1)

        self.assertFalse(self.mc.images['image9'].loaded)
        self.assertFalse(self.mc.images['image9'].loading)
        self.assertFalse(self.mc.images['image9'].unloading)
