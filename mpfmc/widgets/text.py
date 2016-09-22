import re
from kivy.uix.label import Label
from mpfmc.uix.widget import MpfWidget


class Text(MpfWidget, Label):
    widget_type_name = 'Text'
    var_finder = re.compile("(?<=\()[a-zA-Z_0-9|]+(?=\))")
    string_finder = re.compile("(?<=\$)[a-zA-Z_0-9]+")
    merge_settings = ('font_name', 'font_size', 'bold', 'italic', 'halign',
                      'valign', 'padding_x', 'padding_y', 'text_size',
                      'shorten', 'mipmap', 'markup', 'line_height',
                      'max_lines', 'strip', 'shorten_from', 'split_str',
                      'unicode_errors', 'color')

    def __init__(self, mc, config, key=None, play_kwargs=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        self.original_text = self._get_text_string(config.get('text', ''))

        self.text_variables = dict()
        if play_kwargs:
            self.event_replacements = play_kwargs
        else:
            self.event_replacements = kwargs
        self._process_text(self.original_text)

    def __repr__(self):
        return '<Text Widget text={}>'.format(self.text)

    def texture_update(self, *largs):
        super().texture_update(*largs)
        self.size = self.texture_size

    def update_kwargs(self, **kwargs):
        self.event_replacements.update(kwargs)

        self._process_text(self.original_text)

    def _get_text_string(self, text):
        if '$' not in text:
            return text

        for text_string in Text.string_finder.findall(text):
            text = text.replace('${}'.format(text_string),
                                self._do_get_text_string(text_string))

        return text

    def _do_get_text_string(self, text_string):
        try:
            return str(self.mc.machine_config['text_strings'][text_string])
        except (KeyError):
            # if the text string is not found, put the $ back on
            return '${}'.format(text_string)

    def _get_text_vars(self, text):
        return Text.var_finder.findall(text)

    def _process_text(self, text):
        for var_string in self._get_text_vars(text):
            if var_string in self.event_replacements:
                text = text.replace('({})'.format(var_string),
                                    str(self.event_replacements[var_string]))

        if self._get_text_vars(text):
            # monitors won't be added twice, so it's ok to blindly call this
            self._setup_variable_monitors(text)

        self.update_vars_in_text(text)

    def update_vars_in_text(self, text):
        for var_string in self._get_text_vars(text):
            if var_string.startswith('machine|'):
                try:
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.machine_vars[
                                                var_string.split('|')[1]]))
                except KeyError:
                    text = ''

            elif self.mc.player:
                if var_string.startswith('player|'):
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.player[
                                                var_string.split('|')[1]]))
                    continue
                elif var_string.startswith('player') and '|' in var_string:
                    player_num, var_name = var_string.lstrip('player').split(
                            '|')
                    try:
                        value = self.mc.player_list[int(player_num) - 1][
                            var_name]

                        if value is not None:
                            text = text.replace('(' + var_string + ')',
                                                str(value))
                        else:
                            text = ''
                    except IndexError:
                        text = ''
                    continue
                elif self.mc.player.is_player_var(var_string):
                    text = text.replace('(' + var_string + ')',
                                        str(self.mc.player[var_string]))
                    continue

            if var_string in self.event_replacements:
                text = text.replace('({})'.format(var_string),
                    str(self.event_replacements[var_string]))

        self.update_text(text)

    def update_text(self, text):
        if text:
            if self.config['min_digits']:
                text = text.zfill(self.config['min_digits'])

            if self.config['number_grouping']:

                # find the numbers in the string
                number_list = [s for s in text.split() if s.isdigit()]

                # group the numbers and replace them in the string
                for item in number_list:
                    grouped_item = Text.group_digits(item)
                    text = text.replace(str(item), grouped_item)
        self.text = text
        self.texture_update()

    def _player_var_change(self, **kwargs):
        del kwargs

        self.update_vars_in_text(self.original_text)

    def _machine_var_change(self, **kwargs):
        del kwargs
        self.update_vars_in_text(self.original_text)

    def _setup_variable_monitors(self, text):
        for var_string in self._get_text_vars(text):
            if '|' not in var_string:
                self.add_player_var_handler(name=var_string)
                self.add_current_player_handler()
            else:
                source, variable_name = var_string.split('|')
                if source.lower().startswith('player'):

                    if source.lstrip('player'):  # we have player num
                        self.add_player_var_handler(name=variable_name)
                    else:  # no player num
                        self.add_player_var_handler(name=var_string)
                        self.add_current_player_handler()
                elif source.lower() == 'machine':
                    self.add_machine_var_handler(name=variable_name)

    def add_player_var_handler(self, name):
        self.mc.events.add_handler('player_{}'.format(name),
                                   self._player_var_change)

    def add_current_player_handler(self):
        self.mc.events.add_handler('player_turn_start',
                                   self._player_var_change)

    def add_machine_var_handler(self, name):
        self.mc.events.add_handler('machine_var_{}'.format(name),
                                   self._machine_var_change)

    def prepare_for_removal(self):
        self.mc.events.remove_handler(self._player_var_change)
        self.mc.events.remove_handler(self._machine_var_change)

    @staticmethod
    def group_digits(text, separator=',', group_size=3):
        """Enables digit grouping (i.e. adds comma separators between
        thousands digits).

        Args:
            text: The incoming string of text
            separator: String of the character(s) you'd like to add between the
                digit groups. Default is a comma. (",")
            group_size: How many digits you want in each group. Default is 3.

        Returns: A string with the separator added.

        MPF uses this method instead of the Python locale settings because the
        locale settings are a mess. They're set system-wide and it's really
        hard
        to make them work cross-platform and there are all sorts of external
        dependencies, so this is just way easier.

        """
        digit_list = list(text.split('.')[0])

        for i in range(len(digit_list))[::-group_size][1:]:
            digit_list.insert(i + 1, separator)

        return ''.join(digit_list)
