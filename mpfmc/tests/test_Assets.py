import time

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestAssets(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/assets_and_image'

    def get_config_file(self):
        return 'test_asset_loading.yaml'

    def test_machine_wide_asset_loading(self):

        # test that the images asset class gets built correctly
        self.assertTrue(hasattr(self.mc, 'images'))
        self.assertTrue(self.mc.asset_manager._asset_classes)
        self.assertEqual(self.mc.asset_manager._asset_classes[0].path_string, 'images')

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

        # test subfolder under another subfolder listed in assets:images
        self.assertIn('image14', self.mc.images)  # /images/preload/subfolder

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
        self.assertEqual(self.mc.images['image14'].config['test_key'],
                         'test_value')

        # test custom k/v pair from asset entry in the images: section
        self.assertEqual(self.mc.images['image3'].config['test_key'],
                         'test_value_override3')

        # same as above, but test that it also works when the asset name is
        # different from the file name
        self.assertEqual(
                self.mc.images['image_12_new_name'].config['test_key'],
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
            time.sleep(.1)
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

        self.assertFalse(self.mc.images['image6'].loaded)
        self.assertFalse(self.mc.images['image6'].loading)
        self.assertFalse(self.mc.images['image6'].unloading)

        # Start the mode and make sure those assets load
        self.mc.modes['mode1'].start()
        self.advance_time()

        # Give it a second to load. This file is tiny, so it shouldn't take
        # this long
        time.sleep(.001)
        self.advance_time(.1)
        for x in range(10):
            if not self.mc.images['image9'].loaded or not self.mc.images['image6'].loaded:
                time.sleep(.1)
                self.advance_time(.1)

        self.assertTrue(self.mc.images['image9'].loaded)
        self.assertFalse(self.mc.images['image9'].loading)
        self.assertFalse(self.mc.images['image9'].unloading)

        self.assertTrue(self.mc.images['image6'].loaded)
        self.assertFalse(self.mc.images['image6'].loading)
        self.assertFalse(self.mc.images['image6'].unloading)

        # test mode stop which should unload those assets
        self.mc.modes['mode1'].stop()

        for x in range(10):
            if self.mc.images['image9'].loaded:
                self.assertTrue(self.mc.images['image9'].unloading)
                self.advance_time(.1)

        self.assertFalse(self.mc.images['image9'].loaded)
        self.assertFalse(self.mc.images['image9'].loading)
        self.assertFalse(self.mc.images['image9'].unloading)

    def test_random_asset_group(self):
        # three assets, no weights

        # make sure the asset group was created
        self.assertIn('group1', self.mc.images)

        # make sure the randomness is working. To test this, we request the
        # asset 10,000 times and then count the results and assume that each
        # should be 3,333 +- 500 just to make sure the test never fails/
        res = list()
        for x in range(10000):
            res.append(self.mc.images['group1'].image)

        self.assertAlmostEqual(3333, res.count(self.mc.images['image1']),
                               delta=500)
        self.assertAlmostEqual(3333, res.count(self.mc.images['image2']),
                               delta=500)
        self.assertAlmostEqual(3333, res.count(self.mc.images['image3']),
                               delta=500)

    def test_random_asset_group_with_weighting(self):
        # three assets, third one has a weight of 2

        # make sure the asset group was created
        self.assertIn('group2', self.mc.images)

        # make sure the randomness is working. To test this, we request the
        # asset 10,000 times and then count the results and assume that each
        # should be 3,333 +- 500 just to make sure the test never fails/
        res = list()
        for x in range(10000):
            res.append(self.mc.images['group2'].image)

        self.assertAlmostEqual(2500, res.count(self.mc.images['image1']),
                               delta=500)
        self.assertAlmostEqual(2500, res.count(self.mc.images['image2']),
                               delta=500)
        self.assertAlmostEqual(5000, res.count(self.mc.images['image3']),
                               delta=500)

    def test_sequence_asset_group(self):
        # three assets, no weights

        self.assertIn('group3', self.mc.images)

        # Should always return in order, 1, 2, 3, 1, 2, 3...
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image3'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image3'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group3'].image, self.mc.images['image3'])

    def test_sequence_asset_group_with_count(self):
        # three assets, no weights

        self.assertIn('group4', self.mc.images)

        # Should always return in order, 1, 1, 1, 1, 2, 2, 3, 1, 1, 1, 1 ...
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image3'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image1'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image2'])
        self.assertIs(self.mc.images['group4'].image, self.mc.images['image3'])

    def test_random_force_next(self):
        # random, except it ensures the same one does not show up twice in a
        # row

        self.assertIn('group5', self.mc.images)

        # do it 10,000 times just to be sure. :)
        last = self.mc.images['group5'].image
        res = list()

        for x in range(10000):
            image = self.mc.images['group5'].image
            self.assertIsNot(last, image)
            last = image

            res.append(image)

        # Also check that the weights were right

        # BTW these weights are non-intuitive since the last asset is not
        # considered for the next round. e.g. image1 = 1, image2 = 5,
        # image3 = 1, so you'd think they would be 1400, 7200, 1400, but in
        # reality, 50% of the time, asset2 is not in contention, so really
        # asset2 has a 6-to-1 (84%) chance of being selected 66% of the time,
        # but a 0% chance of being selected 33% of the time, etc. So trust that
        # these numbers are right. :)
        self.assertAlmostEqual(2733, res.count(self.mc.images['image1']),
                               delta=500)
        self.assertAlmostEqual(4533, res.count(self.mc.images['image2']),
                               delta=500)
        self.assertAlmostEqual(2733, res.count(self.mc.images['image3']),
                               delta=500)

    def test_random_force_all(self):
        # random, except it ensures the same one does not show up twice before
        # they're all shown

        self.assertIn('group6', self.mc.images)

        for x in range(1000):
            this_set = set()
            this_set.add(self.mc.images['group6'].image)
            this_set.add(self.mc.images['group6'].image)
            this_set.add(self.mc.images['group6'].image)

            self.assertEqual(len(this_set), 3)
