"""BCP Server interface for the MPF Media Controller"""

import logging
import queue
import socket
import sys
import threading
import time
import traceback

import select

import mpf.core.bcp as bcp


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

        self.setup_server_socket()
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
        except IOError:
            self.log.critical('Socket bind IOError')
            raise

        self.socket.listen(5)
        self.socket.settimeout(1)

    def run(self):
        """The socket thread's run loop."""

        try:
            while not self.mc.thread_stopper.is_set():
                self.log.info("Waiting for a connection...")
                self.mc.events.post('client_disconnected',
                                    host=self.socket.getsockname()[0],
                                    port=self.socket.getsockname()[1])
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

                while (not self.connection and
                        not self.mc.thread_stopper.is_set()):
                    try:
                        self.connection, client_address = self.socket.accept()
                    except socket.timeout:
                        if self.mc.thread_stopper.is_set():
                            self.log.info("Stopping BCP listener thread")
                            self.socket.shutdown(socket.SHUT_RDWR)
                            self.socket.close()
                            return

                self.log.info("Received connection from: %s:%s",
                              client_address[0], client_address[1])
                self.mc.events.post('client_connected',
                                    address=client_address[0],
                                    port=client_address[1])
                '''event: client_connected
                desc: Posted on the MPF-MC only when a BCP client has
                connected.

                args:
                address: The IP address of the client that connected.
                port: The port the client connected on.
                '''

                self.mc.bcp_client_connected = True

                # Receive the data in small chunks and retransmit it
                while not self.mc.thread_stopper.is_set():
                    # todo Better large message handling
                    # if a json message comes in that's larger than 8192, it
                    # won't be processed properly. So if we end up sticking
                    # with BCP, we should probably change this to be smarter
                    # and to check for complete messages before processing them

                    try:
                        ready = select.select([self.connection], [], [], 1)
                        if ready[0]:
                            socket_chars = self.connection.recv(8192).decode(
                                'utf-8')
                            if socket_chars:
                                commands = socket_chars.split("\n")
                                for cmd in commands:
                                    if cmd:
                                        self.process_received_message(cmd)
                            else:
                                # no bytes -> socket closed
                                break

                    except socket.timeout:
                        pass

                    except OSError:
                        if self.mc.machine_config['mpf-mc'][
                                'exit_on_disconnect']:
                            self.mc.stop()
                        else:
                            break

                # close connection. while loop will not exit if this is not intended.
                self.connection.close()
                self.connection = None

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value,
                                               exc_traceback)
            msg = ''.join(line for line in lines)
            self.mc.crash_queue.put(msg)

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

        except Exception:
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
