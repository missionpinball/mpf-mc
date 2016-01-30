import re

from kivy.uix.label import Label

from mc.uix.widget import MpfWidget


class Text(MpfWidget, Label):
    widget_type_name = 'Text'
    var_finder = re.compile("(?<=%)[a-zA-Z_0-9|]+(?=%)")
    string_finder = re.compile("(?<=\$)[a-zA-Z_0-9]+")

    def __init__(self, mc, config, slide, text_variables=None, mode=None,
                 priority=0, **kwargs):

        super().__init__(mc=mc, mode=mode, slide=slide, config=config)

        self.original_text = self._get_text_string(config.get('text', ''),
                                                   mode=mode)

        self.text_variables = dict()

        self._process_text(self.text, local_replacements=kwargs,
                           local_type='event', mode=mode)

    def __repr__(self):
        return '<Text Widget text={}>'.format(self.text)

    def texture_update(self, *largs):
        super().texture_update(*largs)
        self.size = self.texture_size

    def _get_text_string(self, text, mode=None):
        if not '$' in text:
            return text

        for text_string in Text.string_finder.findall(text):
            text = text.replace('${}'.format(text_string),
                                self._do_get_text_string(text_string, mode))

        return text

    def _do_get_text_string(self, text_string, mode=None):
        try:
            return str(mode.config['text_strings'][text_string])
        except (AttributeError, KeyError):
            pass

        try:
            return str(self.mc.machine_config['text_strings'][text_string])
        except (KeyError):
            # if the text string is not found, put the $ back on
            return '${}'.format(text_string)

    def _get_text_vars(self):
        return Text.var_finder.findall(self.original_text)

    def _process_text(self, text, local_replacements=None, local_type=None,
                      mode=None):
        # text: source text with placeholder vars
        # local_replacements: dict of var names & their replacements
        # local_type: type specifier of local replacements. e.g. "event" means
        # it will look for %event|var_name% in the text string

        if not local_replacements:
            local_replacements = list()

        for var_string in self._get_text_vars():
            if var_string in local_replacements:
                text = text.replace('%{}%'.format(var_string),
                                    str(local_replacements[var_string]))
                self.original_text = text

            elif local_type and var_string.startswith(local_type + '|'):
                text = text.replace('%{}%'.format(var_string),
                    str(local_replacements[var_string.split('|')[1]]))
                self.original_text = text

        if self._get_text_vars():
            self._setup_variable_monitors()

        self.update_vars_in_text()

    def update_vars_in_text(self):

        text = self.original_text

        for var_string in self._get_text_vars():
            if var_string.startswith('machine|'):
                try:
                    text = text.replace('%' + var_string + '%',
                                        str(self.mc.machine_vars[
                                                var_string.split('|')[1]]))
                except KeyError:
                    text = ''

            elif self.mc.player:
                if var_string.startswith('player|'):
                    text = text.replace('%' + var_string + '%',
                                        str(self.mc.player[
                                                var_string.split('|')[1]]))
                elif var_string.startswith('player'):
                    player_num, var_name = var_string.lstrip('player').split(
                            '|')
                    try:
                        value = self.mc.player_list[int(player_num) - 1][
                            var_name]

                        if value is not None:
                            text = text.replace('%' + var_string + '%',
                                                str(value))
                        else:
                            text = ''
                    except IndexError:
                        text = ''
                else:
                    text = text.replace('%' + var_string + '%',
                                        str(self.mc.player[var_string]))

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
        self.update_vars_in_text()

    def _machine_var_change(self, **kwargs):
        self.update_vars_in_text()

    def _setup_variable_monitors(self):
        for var_string in self._get_text_vars():
            if '|' not in var_string:
                self.add_player_var_handler(name=var_string, player=None)
            else:
                source, variable_name = var_string.split('|')
                if source.lower().startswith('player'):

                    if source.lstrip('player'):
                        self.add_player_var_handler(name=variable_name,
                                                    player=source.lstrip(
                                                            'player'))
                    else:
                        self.add_player_var_handler(name=var_string,
                                                    player=self.mc.player[
                                                        'number'])

                elif source.lower() == 'machine':
                    self.add_machine_var_handler(name=variable_name)

    def add_player_var_handler(self, name, player):
        self.mc.events.add_handler('player_' + name,
                                        self._player_var_change,
                                        target_player=player,
                                        var_name=name)

    def add_machine_var_handler(self, name):
        self.mc.events.add_handler('machine_var_' + name,
                                        self._machine_var_change,
                                        var_name=name)

    def prepare_for_removal(self, widget):
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
