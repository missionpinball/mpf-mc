"""BCP Settings Controller for MC."""
from mpf.core.settings_controller import SettingsController, SettingEntry


class McSettingsController(SettingsController):

    """MC Settings Controller.

    Gets settings via BCP. Can also set settings using bcp.
    """

    def _add_entries_from_config(self):
        """Do not load entries from config."""

    def add_setting(self, setting):
        """Add a setting."""
        setting = SettingEntry(*setting)
        self._settings[setting.name] = setting
