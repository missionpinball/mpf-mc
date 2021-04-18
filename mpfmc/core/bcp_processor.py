from copy import deepcopy

import queue
import logging
from distutils.version import LooseVersion

import psutil
from kivy.clock import Clock

import mpf.core.bcp.bcp_socket_client as bcp
from mpfmc._version import __bcp_version__, version as mc_version, extended_version as mc_extended_version
from mpfmc.core.bcp_server import BCPServer


class BcpProcessor:
    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('BcpProcessor')

        self.socket_thread = None
        self.connected = False
        self.receive_queue = queue.Queue()
        self.sending_queue = queue.Queue()
        self.mc_process = psutil.Process()

        if self.mc.options['bcp']:
            self.mc.events.add_handler('init_done', self._start_socket_thread)
            self.enabled = True
        else:
            self.enabled = False

        self.debug_log = self.mc.machine_config['bcp']['debug']

        self.bcp_commands = {'error': self._bcp_error,
                             'goodbye': self._bcp_goodbye,
                             'hello': self._bcp_hello,
                             'machine_variable': self._bcp_machine_variable,
                             'mode_start': self._bcp_mode_start,
                             'mode_stop': self._bcp_mode_stop,
                             'mode_list': self._bcp_mode_list,
                             'ball_start': self._bcp_ball_start,
                             'ball_end': self._bcp_ball_end,
                             'player_added': self._bcp_player_add,
                             'player_turn_start': self._bcp_player_turn_start,
                             'player_variable': self._bcp_player_variable,
                             'reset': self._bcp_reset,
                             'settings': self._bcp_settings,
                             'status_request': self._bcp_status_request,
                             'switch': self._bcp_switch,
                             'trigger': self._bcp_trigger,
                             }

        self.mc.events.add_handler('client_connected', self._client_connected)
        self.mc.events.add_handler('mc_reset_complete', self._reset_complete)

        Clock.schedule_interval(self._get_from_queue, 0)

    def _client_connected(self, **kwargs):
        del kwargs
        self.send(bcp_command="set_machine_var", name="mc_version", value=mc_version)
        self.send(bcp_command="set_machine_var", name="mc_extended_version", value=mc_extended_version)
        self.send(bcp_command="monitor_start", category="machine_vars")
        self.send(bcp_command="monitor_start", category="player_vars")
        self.send(bcp_command="monitor_start", category="modes")
        self.send(bcp_command="monitor_start", category="core_events")
        self.send(bcp_command="monitor_start", category="status_request")
        self.register_trigger("master_volume_increase")
        self.register_trigger("master_volume_decrease")
        self.register_trigger("debug_dump_stats")
        self.register_trigger("update_segment_display")
        self.connected = True

    def register_trigger(self, event):
        """Register a trigger for events from MPF."""
        self.send("register_trigger", event=event)

    def remove_trigger(self, event):
        """Remove/unregister a trigger for events from MPF."""
        self.send("remove_trigger", event=event)

    def _start_socket_thread(self, **kwargs):
        del kwargs

        if self.socket_thread:
            return

        self.socket_thread = BCPServer(self.mc, self.receive_queue,
                                       self.sending_queue)
        self.socket_thread.daemon = True
        self.socket_thread.start()

        self.mc.events.remove_handler(self._start_socket_thread)

    def send(self, bcp_command, callback=None, rawbytes=None, **kwargs):
        """Sends a BCP command to the connected pinball controller.

        Note that if the BCP server is not running, this method will just throw
        the BCP away. (It will still call the callback in that case.

        Args:
            bcp_command: String of the BCP command name.
            callback: Optional callback method that will be called when the
                command is sent.
            **kwargs: Optional additional kwargs will be added to the BCP
                command string.

        """
        if self.enabled:
            if not self.mc.bcp_client_connected:
                raise AssertionError("Not connected to MPF.")

            self.sending_queue.put(
                (bcp.encode_command_string(bcp_command, **kwargs), rawbytes))

        if callback:
            callback()

    def receive_bcp_message(self, msg):
        """Receives an incoming BCP message to be processed.

        Note this method is intended for testing. Usually BCP messages are
        handled by the BCP Server thread, but for test purposes it's possible
        to run mpf-mc without the BCP Server, so in that case you can use this
        method to send BCP messages into the mpf-mc.

        Args:
            msg: A string of the BCP message (in the standard BCP format:
                command?param1=value1&param2=value2...

        """
        cmd, kwargs = bcp.decode_command_string(msg)
        self.receive_queue.put((cmd, kwargs))

    def _get_from_queue(self, dt):
        """Gets and processes all queued up incoming BCP commands."""
        del dt

        while not self.receive_queue.empty():
            cmd, kwargs = self.receive_queue.get(False)
            self._process_command(cmd, **kwargs)

    def _process_command(self, bcp_command, **kwargs):
        if self.debug_log:
            if 'rawbytes' in kwargs:
                debug_kwargs = deepcopy(kwargs)
                debug_kwargs['rawbytes'] = '<{} bytes>'.format(
                    len(debug_kwargs.pop('rawbytes')))

                self.log.debug("Processing command: %s %s", bcp_command,
                               debug_kwargs)
            else:
                self.log.debug("Processing command: %s %s", bcp_command,
                               kwargs)

        # Can't use try/except KeyError here because there could be a KeyError
        # in the callback which we don't want it to swallow.
        if bcp_command in self.bcp_commands:
            self.bcp_commands[bcp_command](**kwargs)
        else:
            self.log.warning("Received invalid BCP command: %s", bcp_command[:9])
            # self.send('error',message='invalid command', command=bcp_command)

    def _bcp_status_request(self, **kwargs):
        """Status request."""
        del kwargs

        self.send("status_report",
                  cpu=self.mc_process.cpu_percent(),
                  rss=self.mc_process.memory_info().rss,
                  vms=self.mc_process.memory_info().vms)

    def _bcp_hello(self, **kwargs):
        """Processes an incoming BCP 'hello' command."""
        try:
            if LooseVersion(kwargs['version']) == (
                    LooseVersion(__bcp_version__)):
                self.send('hello', version=__bcp_version__)
            else:
                self.send('hello', version='unknown protocol version')
        except KeyError:
            self.log.warning("Received invalid 'version' parameter with 'hello'")

    def _bcp_goodbye(self, **kwargs):
        """Processes an incoming BCP 'goodbye' command."""
        # if self.config['mpf-mc']['exit_on_disconnect']:
        #     self.socket_thread.sending_thread.stop()
        #     sys.exit()

    def _bcp_mode_start(self, name=None, priority=0, **kwargs):
        """Processes an incoming BCP 'mode_start' command."""
        del kwargs

        if not name:
            return
            # todo raise error

        if name == 'game':
            self.mc.game_start()

        if name in self.mc.modes:
            self.mc.modes[name].start(mode_priority=int(priority))

    def _bcp_mode_list(self, **kwargs):
        pass

    def _bcp_mode_stop(self, name, **kwargs):
        """Processes an incoming BCP 'mode_stop' command."""
        del kwargs
        if not name:
            return
            # todo raise error

        if name == 'game':
            self.mc.game_end()

        if name in self.mc.modes:
            self.mc.modes[name].stop()

    @staticmethod
    def _bcp_ball_start(player_num, ball, **kwargs):
        del player_num, ball, kwargs

    @staticmethod
    def _bcp_ball_end(**kwargs):
        del kwargs

    def _bcp_settings(self, settings, **kwargs):
        del kwargs
        for setting in settings:
            self.mc.settings.add_setting(setting)

    def _bcp_error(self, **kwargs):
        """Processes an incoming BCP 'error' command."""
        del kwargs
        self.log.warning('Received error command from client')

    def _bcp_player_add(self, player_num, **kwargs):
        """Processes an incoming BCP 'player_add' command."""
        del kwargs
        self.mc.add_player(int(player_num))

    # pylint: disable-msg=too-many-arguments
    def _bcp_player_variable(self, name, value, prev_value, change, player_num,
                             **kwargs):
        """Processes an incoming BCP 'player_variable' command."""
        del prev_value
        del change
        del kwargs
        self.mc.update_player_var(name, value, int(player_num))

    def send_machine_var_to_mpf(self, name, value):
        """Set machine var in MPF via BCP."""
        self.send("set_machine_var", name=name, value=value)

    def _bcp_machine_variable(self, name, value, change=True, prev_value=None,
                              **kwargs):
        """Processes an incoming BCP 'machine_variable' command."""
        del kwargs
        self.mc.receive_machine_var_update(name, value, change, prev_value)

    def _bcp_player_turn_start(self, player_num, **kwargs):
        """Processes an incoming BCP 'player_turn_start' command."""
        del kwargs
        self.mc.player_start_turn(int(player_num))

    def _bcp_trigger(self, name, **kwargs):
        """Processes an incoming BCP 'trigger' command."""
        self.mc.events.post(name, **kwargs)

    def _bcp_switch(self, name, state, **kwargs):
        """Processes an incoming BCP 'switch' command."""
        del kwargs
        if int(state):
            self.mc.events.post('switch_' + name + '_active')
            '''event: switch_(name)_active
            config_section: switches
            class_label: switch

            desc: Posted on MPF-MC only (e.g. not in MPF) when the MC receives
            a BCP "switch" active command. Useful for video modes and graphical
            menu navigation. Note that this is not posted for every switch all
            the time, rather, only for switches that have been configured to
            send events to BCP.
            '''
        else:
            self.mc.events.post('switch_' + name + '_inactive')
            '''event: switch_(name)_inactive
            config_section: switches
            class_label: switch

            desc: Posted on MPF-MC only (e.g. not in MPF) when the MC receives
            a BCP "switch" inactive command. Useful for video modes and graphical
            menu navigation. Note that this is not posted for every switch all
            the time, rather, only for switches that have been configured to
            send events to BCP.
            '''

    def _bcp_reset(self, **kwargs):
        del kwargs
        self.mc.reset()

    def _reset_complete(self, **kwargs):
        del kwargs
        self.send('reset_complete')
