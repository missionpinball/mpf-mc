import queue
import logging
from distutils.version import LooseVersion

from kivy.clock import Clock

import mpf.core.bcp as bcp
from mpfmc._version import __bcp_version__
from mpfmc.core.bcp_server import BCPServer


class BcpProcessor(object):
    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('BcpProcessor')

        self.socket_thread = None
        self.receive_queue = queue.Queue()
        self.sending_queue = queue.Queue()

        if self.mc.options['bcp']:
            self.mc.events.add_handler('init_done', self._start_socket_thread)
            self.enabled = True
        else:
            self.enabled = False

        self.bcp_commands = {'config': self._bcp_config,
                             'dmd_start': self._bcp_dmd_start,
                             'error': self._bcp_error,
                             'get': self._bcp_get,
                             'goodbye': self._bcp_goodbye,
                             'hello': self._bcp_hello,
                             'machine_variable': self._bcp_machine_variable,
                             'mode_start': self._bcp_mode_start,
                             'mode_stop': self._bcp_mode_stop,
                             'player_added': self._bcp_player_add,
                             'player_score': self._bcp_player_score,
                             'player_turn_start': self._bcp_player_turn_start,
                             'player_variable': self._bcp_player_variable,
                             'reset': self._bcp_reset,
                             'rgb_dmd_start': self._bcp_rgb_dmd_start,
                             'set': self._bcp_set,
                             'switch': self._bcp_switch,
                             'trigger': self._bcp_trigger,
                             }

        Clock.schedule_interval(self._get_from_queue, 0)

    def _start_socket_thread(self):

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
        if self.enabled and self.mc.bcp_client_connected:

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
        self.log.debug("Processing command: %s %s", bcp_command, kwargs)

        # Can't use try/except KeyError here becasue there could be a KeyError
        # in the callback which we don't want it to swallow.
        if bcp_command in self.bcp_commands:
            self.bcp_commands[bcp_command](**kwargs)
        else:
            self.log.warning("Received invalid BCP command: %s", bcp_command[:9])
            # self.send('error',message='invalid command', command=bcp_command)

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

        pass  # todo

    def _bcp_mode_start(self, name=None, priority=0, **kwargs):
        """Processes an incoming BCP 'mode_start' command."""
        del kwargs

        if not name:
            return
            # todo raise error

        if name == 'game':
            self.mc.game_start()

        if name in self.mc.modes:
            self.mc.modes[name].start(priority=int(priority))

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

    def _bcp_error(self, **kwargs):
        """Processes an incoming BCP 'error' command."""
        del kwargs
        self.log.warning('Received error command from client')

    def _bcp_player_add(self, player_num, **kwargs):
        """Processes an incoming BCP 'player_add' command."""
        del kwargs
        self.mc.add_player(int(player_num))

    def _bcp_player_variable(self, name, value, prev_value, change, player_num,
                             **kwargs):
        """Processes an incoming BCP 'player_variable' command."""
        del prev_value
        del change
        del kwargs
        self.mc.update_player_var(name, value, int(player_num))

    def _bcp_machine_variable(self, name, value, change=True, prev_value=None,
                              **kwargs):
        """Processes an incoming BCP 'machine_variable' command."""
        del kwargs
        self.mc.set_machine_var(name, value, change, prev_value)

    def _bcp_player_score(self, value, prev_value, change, player_num,
                          **kwargs):
        """Processes an incoming BCP 'player_score' command."""
        del change
        del prev_value
        del kwargs
        self.mc.update_player_var('score', value, int(player_num))

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
            desc: Posted on MPF-MC only (e.g. not in MPF) when the MC receives
            a BCP "switch" active command. Useful for video modes and graphical
            menu navigation. Note that this is not posted for every switch all
            the time, rather, only for switches that have been configured to
            send events to BCP.
            '''
        else:
            self.mc.events.post('switch_' + name + '_inactive')
            '''event: switch_(name)_inactive
            desc: Posted on MPF-MC only (e.g. not in MPF) when the MC receives
            a BCP "switch" inactive command. Useful for video modes and graphical
            menu navigation. Note that this is not posted for every switch all
            the time, rather, only for switches that have been configured to
            send events to BCP.
            '''

    def _bcp_get(self, **kwargs):
        """Processes an incoming BCP 'get' command by posting an event
        'bcp_get_<name>'. It's up to an event handler to register for that
        event and to send the response BCP 'set' command.

        """
        # for name in Util.string_to_list(names):
        #     self.mc.events.post('bcp_get_{}'.format(name))

        pass  # todo

    def _bcp_set(self, **kwargs):
        """Processes an incoming BCP 'set' command by posting an event
        'bcp_set_<name>' with a parameter value=<value>. It's up to an event
        handler to register for that event and to do something with it.

        Note that BCP set commands can contain multiple key/value pairs, and
        this method will post one event for each pair.

        """
        for k, v in kwargs.items():
            self.mc.events.post('bcp_set_{}'.format(k), value=v)
            # docstring covered in MPF

    def _bcp_config(self, **kwargs):
        """Processes an incoming BCP 'config' command."""
        # for k, v in kwargs.iteritems():
        #     if k.startswith('volume_'):
        #         self.bcp_set_volume(track=k.split('volume_')[1], value=v)

        pass  # todo

    def _bcp_set_volume(self, track, value):
        """Sets the volume based on an incoming BCP 'config' command.

        Args:
            track: String name of the track the volume will set.
            value: Float between 0 and 1 which represents the volume level to
                set.

        Note: At this time only the master volume can be set with this method.

        """
        if track == 'master':
            self.sound.set_volume(value)

            # if track in self.sound.tracks:
            # self.sound.tracks[track]

            # todo add per-track volume support to sound system

    def _bcp_reset(self, **kwargs):
        del kwargs
        self.mc.reset()

        # temp todo
        self.send('reset_complete')

    def _bcp_dmd_start(self, fps):
        self.mc.create_physical_dmd(fps)

    def _bcp_rgb_dmd_start(self, fps):
        self.mc.create_physical_rgb_dmd(fps)
