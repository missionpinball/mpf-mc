"""BCP Server interface for the MPF Media Controller"""

import logging
import queue
import socket
import sys
import threading
import time
import traceback

import select

import mpf.core.bcp.bcp_socket_client as bcp
from mpf.exceptions.runtime_error import MpfRuntimeError


class BCPServer(threading.Thread):
    """Parent class for the BCP Server thread.

    Args:
        mc: A reference to the main MediaController instance.
        receiving_queue: A shared Queue() object which holds incoming BCP
            commands.
        sending_queue: A shared Queue() object which holds outgoing BCP
            commands.

    """

    def __init__(self, mc, receiving_queue, sending_queue):

        threading.Thread.__init__(self)
        self.mc = mc
        self.log = logging.getLogger('MPF-MC BCP Server')
        self.receive_queue = receiving_queue
        self.sending_queue = sending_queue
        self.connection = None
        self.socket = None
        self.done = False

        self.setup_server_socket(mc.machine_config['mpf-mc']['bcp_interface'],
                                 mc.machine_config['mpf-mc']['bcp_port'])
        self.sending_thread = threading.Thread(target=self.sending_loop)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def setup_server_socket(self, interface='localhost', port=5050):
        """Sets up the socket listener.

        Args:
            interface: String name of which interface this socket will listen
                on.
            port: Integer TCP port number the socket will listen on.

        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.log.info('Starting up on %s port %s', interface, port)

        try:
            self.socket.bind((interface, port))
        except IOError as e:
            raise MpfRuntimeError("Failed to bind BCP Socket to {} on port {}. "
                                  "Is there another application running on that port?".format(interface, port), 1,
                                  self.log.name) from e

        self.socket.listen(5)
        self.socket.settimeout(1)

    def _connect(self):
        self.log.info("Waiting for a connection...")
        # Since posting an event from a thread is not safe, we just
        # drop the event we want into the receive queue and let the
        # main loop pick it up
        self.receive_queue.put(('trigger',
                                {'name': 'client_disconnected',
                                 'host': self.socket.getsockname()[0],
                                 'port': self.socket.getsockname()[1]}))
        '''event: client_disconnected
        desc: Posted on the MPF-MC only (e.g. not in MPF) when the BCP
        client disconnects. This event is also posted when the MPF-MC
        starts before a client is connected.

        This is useful for triggering a slide notifying of the
        disconnect.

        args:
        host: The hostname or IP address that the socket is listening
        on.
        port: The port that the socket is listening on.

        '''
        self.mc.bcp_client_connected = False

        start_time = time.time()
        while (not self.connection and
               not self.mc.thread_stopper.is_set()):
            try:
                self.connection, client_address = self.socket.accept()
            except (socket.timeout, OSError):
                if self.mc.options['production'] and start_time + 30 < time.time():
                    self.log.warning("Timeout while waiting for connection. Stopping!")
                    self.mc.stop()
                    return False
                if self.mc.thread_stopper.is_set():
                    self.log.info("Stopping BCP listener thread")
                    return False

        self.log.info("Received connection from: %s:%s",
                      client_address[0], client_address[1])

        # Since posting an event from a thread is not safe, we just
        # drop the event we want into the receive queue and let the
        # main loop pick it up
        self.receive_queue.put(('trigger',
                                {'name': 'client_connected',
                                 'host': client_address[0],
                                 'port': client_address[1]}))

        '''event: client_connected
        desc: Posted on the MPF-MC only when a BCP client has
        connected.

        args:
        address: The IP address of the client that connected.
        port: The port the client connected on.
        '''
        self.mc.bcp_client_connected = True

        return True

    def run(self):
        """The socket thread's run loop."""
        try:
            while not self.mc.thread_stopper.is_set():
                if not self._connect():
                    return

                socket_chars = b''

                if sys.platform in ("linux", "darwin"):
                    poller = select.poll()
                    poller.register(self.connection, select.POLLIN)

                # Receive the data in small chunks and retransmit it
                while not self.mc.thread_stopper.is_set():
                    if sys.platform in ("linux", "darwin"):
                        ready = poller.poll(None)
                    else:
                        ready = select.select([self.connection], [], [], 1)
                    if ready[0]:
                        try:
                            data_read = self.connection.recv(8192)
                        except socket.timeout:
                            pass

                        if data_read:
                            socket_chars += data_read
                            commands = socket_chars.split(b"\n")

                            # keep last incomplete command
                            socket_chars = commands.pop()

                            # process all complete commands
                            self._process_receives_messages(commands)
                        else:
                            # no bytes -> socket closed
                            break

                # close connection. while loop will not exit if this is not intended.
                self.connection.close()
                self.connection = None

                # always exit
                self.mc.stop()
                return

        except Exception:   # noqa
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value,
                                               exc_traceback)
            msg = ''.join(line for line in lines)
            self.mc.crash_queue.put(msg)

    def _process_receives_messages(self, commands):
        # process all complete commands
        for cmd in commands:
            if cmd:
                try:
                    decoded_cmd = cmd.strip().decode()
                except UnicodeDecodeError:
                    self.log.warning("Failed to decode BCP message: %s", cmd.strip())
                    continue

                self.process_received_message(decoded_cmd)

    def stop(self):
        """ Stops and shuts down the BCP server."""
        if not self.done:
            self.log.info("Socket thread stopping.")
            self.sending_queue.put('goodbye', None)
            time.sleep(1)  # give it a chance to send goodbye before quitting
            self.done = True
            self.mc.done = True

    def sending_loop(self):
        """Sending loop which transmits data from the sending queue to the
        remote socket.

        This method is run as a thread.
        """
        try:
            while not self.done and not self.mc.thread_stopper.is_set():
                try:
                    msg, rawbytes = self.sending_queue.get(block=True,
                                                           timeout=1)

                except queue.Empty:
                    if self.mc.thread_stopper.is_set():
                        self.log.info("Stopping BCP sending thread")
                        self.socket.shutdown(socket.SHUT_RDWR)
                        self.socket.close()
                        self.socket = None
                        return

                    else:
                        continue

                if not rawbytes:
                    self.connection.sendall(('{}\n'.format(msg)).encode('utf-8'))

                else:
                    self.connection.sendall('{}&bytes={}\n'.format(
                        msg, len(rawbytes)).encode('utf-8'))
                    self.connection.sendall(rawbytes)

        except Exception:   # noqa
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value,
                                               exc_traceback)
            msg = ''.join(line for line in lines)
            self.mc.crash_queue.put(msg)

            # todo this does not crash mpf-mc

    def process_received_message(self, message):
        """Puts a received BCP message into the receiving queue.

        Args:
            message: The incoming BCP message

        """
        self.log.debug('Received "%s"', message)

        try:
            cmd, kwargs = bcp.decode_command_string(message)
            self.receive_queue.put((cmd, kwargs))
        except ValueError:
            self.log.error("DECODE BCP ERROR. Message: %s", message)
            raise
