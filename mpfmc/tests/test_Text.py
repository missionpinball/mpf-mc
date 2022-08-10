from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestText(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/text'

    def get_config_file(self):
        return 'test_text.yaml'

    def get_widget(self, index=0):
        return self.mc.targets['default'].current_slide.widgets[index].widget

    def test_static_text(self):
        # Very basic test
        self.mc.events.post('static_text')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'TEST')

    def test_text_from_event_param1(self):
        # widget text is only from event param
        self.mc.events.post('text_from_event_param1', param1='HELLO')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'HELLO')

        # now make sure if we post the event again, the text updates
        self.mc.events.post('text_from_event_param1', param1='THIS')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'THIS')

        self.mc.events.post('text_from_event_param1', param1='IS')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'IS')

        self.mc.events.post('text_from_event_param1', param1='A')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'A')

        self.mc.events.post('text_from_event_param1', param1='NEW')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'NEW')

        self.mc.events.post('text_from_event_param1', param1='EVENT')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'EVENT')

    def test_text_from_event_param2(self):
        # widget text puts static text before param text
        self.mc.events.post('text_from_event_param2', param1='HELLO')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'HI HELLO')

    def test_text_from_event_param3(self):
        # widget text puts static text before and after param text
        self.mc.events.post('text_from_event_param3', param1='AND')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'MIX AND MATCH')

    def test_text_from_event_param4(self):
        # static and event text with no space between
        self.mc.events.post('text_from_event_param4', param1='SPACE')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'NOSPACE')

    def test_text_from_event_param5(self):
        #test event text that comes in as non-string
        self.mc.events.post('text_from_event_param5', param1=1)
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'NUMBER 1')

    def test_text_from_event_param6(self):
        # placeholder for event text for a param that doesn't exist
        self.mc.events.post('text_from_event_param6')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '(param1)')

    def test_text_from_event_param7(self):
        # test percent sign hard coded
        self.mc.events.post('text_from_event_param7')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '1)')

    def test_text_from_event_param8(self):
        # test parenthesis next to placeholder text
        self.mc.events.post('text_from_event_param8', param1=100)
        self.advance_time()

        self.assertEqual(self.get_widget().text, '(100)')

    def test_player_var1(self):
        # staight var, no player specified
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        self.mc.player.test_var = 1

        self.mc.events.post('text_with_player_var1')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '1')
        old_width = self.get_widget().width

        # update var, should update widget
        for x in range(99):
            self.mc.player.test_var += 1
            self.advance_time(.01)

        self.advance_time()
        self.assertEqual(self.get_widget().text, '100')
        self.assertGreater(self.get_widget().width, old_width)

    def test_player_var2(self):
        # 'player' specified
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        self.mc.player.test_var = 1

        self.mc.events.post('text_with_player_var2')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '1')

    def test_player_var3(self):
        # 'player1' specified
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        self.mc.player.test_var = 1

        self.mc.events.post('text_with_player_var3')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '1')

    def test_player_var4(self):
        # 'player2' specified with no player 2. Should be blank.
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        self.mc.player.test_var = 1

        self.mc.events.post('text_with_player_var4')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '')

        # Add player 2 & set the value. Widget should update
        self.mc.add_player(2)
        self.mc.player_list[1].test_var = 'Player 2 test variable'
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Player 2 test variable')

    def test_position_rounding(self):
        # staight var, no player specified
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        # set var, should update widget with even pixel width and not offset
        self.mc.player.test_var = 'its even'
        self.mc.events.post('text_with_player_var1')
        self.advance_time()

        self.get_widget()._round_anchor_styles = ('left', None)

        bounding_box = self.get_widget().canvas.children[-1]
        self.assertEqual(self.get_widget().text, 'its even')
        self.assertAlmostEqual(bounding_box.size[0], 343, delta=5)
        self.assertAlmostEqual(bounding_box.size[1], 118, delta=5)
        self.assertAlmostEqual(bounding_box.pos[0], 200, delta=5)
        self.assertAlmostEqual(bounding_box.pos[1], 150, delta=5)

        # update var, should update widget with an odd pixel width and offset DOWN
        self.mc.player.test_var = 'odd'
        self.advance_time()

        bounding_box = self.get_widget().canvas.children[-1]
        self.assertEqual(self.get_widget().text, 'odd')
        self.assertAlmostEqual(bounding_box.size[0], 170, delta=5)
        self.assertAlmostEqual(bounding_box.size[1], 118, delta=5)
        self.assertAlmostEqual(bounding_box.pos[0], 200, delta=5)
        self.assertAlmostEqual(bounding_box.pos[1], 150, delta=5)

        # update var, should update widget with an odd pixel width and offset UP
        self.get_widget()._round_anchor_styles = ('right', None)
        self.mc.player.test_var = 'also odd'
        self.advance_time()

        bounding_box = self.get_widget().canvas.children[-1]
        self.assertEqual(self.get_widget().text, 'also odd')
        self.assertAlmostEqual(bounding_box.size[0], 382, delta=5)
        self.assertAlmostEqual(bounding_box.size[1], 118, delta=5)
        self.assertAlmostEqual(bounding_box.pos[0], 200, delta=5)
        self.assertAlmostEqual(bounding_box.pos[1], 150, delta=5)

        # update var, should update widget with an even pixel width and not offset
        self.mc.player.test_var = 'no round'
        self.advance_time()

        bounding_box = self.get_widget().canvas.children[-1]
        self.assertEqual(self.get_widget().text, 'no round')
        self.assertAlmostEqual(bounding_box.size[0], 395, delta=5)
        self.assertAlmostEqual(bounding_box.size[1], 118, delta=5)
        self.assertAlmostEqual(bounding_box.pos[0], 200, delta=5)
        self.assertAlmostEqual(bounding_box.pos[1], 150, delta=5)

    def test_current_player(self):
        # verifies that current player text update when current player changes
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)  # Player 1
        self.advance_time()
        self.mc.add_player(2)  # Player 2
        self.advance_time()
        self.mc.add_player(3)  # Player 3
        self.advance_time()

        # Test text: (test_var)

        # Player 1
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertEqual(0, self.mc.player.index)
        self.assertEqual(1, self.mc.player.number)

        self.mc.player.test_var = 'Player 1 test var'
        self.mc.events.post('text_with_player_var1')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'Player 1 test var')

        # Player 2
        self.mc.player_start_turn(2)
        self.advance_time()

        self.assertEqual(1, self.mc.player.index)
        self.assertEqual(2, self.mc.player.number)

        self.mc.player.test_var = 'Player 2 test var'
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'Player 2 test var')

        # Player 3
        self.mc.player_start_turn(3)
        self.advance_time()

        self.assertEqual(2, self.mc.player.index)
        self.assertEqual(3, self.mc.player.number)

        self.mc.player.test_var = 'Player 3 test var'
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'Player 3 test var')

        # Back to player 1, make sure it's still there
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'Player 1 test var')

        # Test text: (player|test_var)
        self.mc.events.post('text_with_player_var2')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Player 1 test var')

        self.mc.player_start_turn(2)
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Player 2 test var')

        self.mc.player_start_turn(3)
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Player 3 test var')

    def test_mix_player_var_and_event_param(self):
        self.mc.game_start()
        self.advance_time()
        self.mc.add_player(1)
        self.advance_time()
        self.mc.player_start_turn(1)
        self.advance_time()

        self.assertTrue(self.mc.player)

        self.mc.player.player_var = 'PLAYER VAR'

        self.mc.events.post('text_with_player_var_and_event',
                            test_param="EVENT PARAM")
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'PLAYER VAR EVENT PARAM')

        self.mc.player.player_var = 'NEW PLAYER VAR'
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'NEW PLAYER VAR EVENT PARAM')

        self.mc.events.post('text_with_player_var_and_event',
                            test_param="NEW EVENT PARAM")
        self.advance_time()
        self.assertEqual(self.get_widget().text,
                         'NEW PLAYER VAR NEW EVENT PARAM')

    def test_number_grouping(self):
        self.mc.events.post('number_grouping')
        self.advance_time()

        # should be 00 even though text is 0
        self.assertEqual(self.get_widget().text, '00')
        self.advance_time()

        self.get_widget().update_text('2000000')
        self.assertEqual(self.get_widget().text, '2,000,000')
        self.advance_time()

    def test_text_casing(self):
        self.mc.events.post('text_nocase')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'sAmPlE tExT caSiNg')

        self.mc.events.post('text_lower')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'sample text casing')

        self.mc.events.post('text_upper')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'SAMPLE TEXT CASING')

        self.mc.events.post('text_title')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Sample Text Casing')

        self.mc.events.post('text_capitalize')
        self.advance_time()
        self.assertEqual(self.get_widget().text, 'Sample text casing')

    def test_text_string1(self):
        # simple text string in machine config
        self.mc.events.post('text_string1')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'HELLO')

    def test_text_string2(self):
        # two text strings in machine config
        self.mc.events.post('text_string2')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'HELLO PLAYER')

    def test_text_string3(self):
        # text string not found
        self.mc.events.post('text_string3')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '$money')

    def test_text_string4(self):
        # text string found with extra dollar sign in text
        self.mc.events.post('text_string4')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '$100')

    def test_custom_fonts(self):
        self.mc.events.post('mpfmc_font')
        self.advance_time()
        self.assertEqual('pixelmix', self.get_widget().font_name)
        self.mc.events.post('machine_font')
        self.advance_time()
        self.assertEqual('big_noodle_titling', self.get_widget().font_name)

    def test_baseline(self):
        self.mc.events.post('baseline')
        self.advance_time()

        # Baseline anchored widgets should all have the same local coordinates
        self.assertEqual(self.get_widget(0).pos[1], 100)
        self.assertEqual(self.get_widget(1).pos[1], 100)
        self.assertEqual(self.get_widget(2).pos[1], 100)
        self.assertEqual(self.get_widget(3).pos[1], 100)

        # Now convert the widget coordinates to parent coordinates for comparison
        widget0 = self.get_widget(0).parent.to_parent(0, self.get_widget(0).pos[1])
        widget1 = self.get_widget(1).parent.to_parent(0, self.get_widget(1).pos[1])
        widget2 = self.get_widget(2).parent.to_parent(0, self.get_widget(2).pos[1])
        widget3 = self.get_widget(3).parent.to_parent(0, self.get_widget(3).pos[1])

        # Baseline anchored widgets should be 4px lower
        self.assertEqual(widget0[1], 100)
        self.assertEqual(widget1[1], 96)
        self.assertEqual(widget2[1], 100)
        self.assertEqual(widget3[1], 96)

    def test_line_break(self):
        """Tests line break in text (multiple lines)"""
        self.mc.events.post('text_line_break')
        self.advance_time()
        self.assertGreater(self.get_widget().height, 40)

    def test_no_multiline(self):
        """Tests poorly formatted YAML line break in text"""
        self.mc.events.post('text_bad_line_break')
        self.advance_time()
        self.assertLess(self.get_widget().height, 30)
