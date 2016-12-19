from mpf.core.placeholder_manager import MachinePlaceholder, BasePlaceholderManager


class McPlaceholderManager(BasePlaceholderManager):

    """Manages templates and placeholders for MC."""

    def get_global_parameters(self, name):
        """Return global params."""
        if name == "settings":
            return self.machine.settings
        elif name == "machine":
            return MachinePlaceholder(self.machine)
        elif self.machine.player:
            if name == "current_player":
                return self.machine.player
            elif name == "players":
                return self.machine.player_list
        return False
