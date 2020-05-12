# External Dependencies
from threading import Thread
import logging
import queue
import ruamel.yaml
import serial
import struct
import time

from laserinterface.data.grbl_doc import COMMANDS

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile, )['GRBL']


class GrblInterface:
    def __init__(self, terminal=None, machine=None):
        # Store or Create terminal and state instance
        self.terminal = terminal
        self.machine = machine

        self.ser = serial.serial_for_url(
            url=config['PORT'],
            baudrate=config['BAUDRATE'],
            timeout=20,
            write_timeout=0,
            do_not_open=True,
        )

        # Variable to store class states
        self._quit = False
        self.chars_in_buffer = queue.Queue()
        self.lines_to_sent = queue.Queue()
        self.lines_count = 0
        self.connected = False
        self.report = '<>'
        self.requested_config = False

    def set_port(self, port):
        if self.connected:
            self.disconnect()
            self.ser.port = port
            self.connect()
            return self.connected

        else:
            self.ser.port = port
            return self.connected

    def connect(self):
        ''' Connect to the configured serial port. also starts 3 threads for:
        sending gcode, requesting state, and handling responses'''

        _log.info(f'connecting to {self.ser.port}')
        try:
            self.ser.open()
        except serial.SerialException:
            _log.info(f'Failed to connect to {self.ser.port}')
            self.connected = False
            return False

        self.thread_receiver = Thread(
            target=self._receive_continuously, daemon=True)
        self.thread_receiver.start()

        self.connected = True
        time.sleep(0.5)
        self.ser.write('\r\n\r\n'.encode('utf-8'))
        time.sleep(0.5)

        self.thread_poll_report = Thread(
            target=self._request_state, daemon=True)
        self.thread_poll_report.start()

        self.thread_send_gcode = Thread(target=self._gcode_sender, daemon=True)
        self.thread_send_gcode.start()

        self.get_config()

        return True

    def disconnect(self):
        ''' set flag to stop the threads, then close the connection '''
        self._quit = True
        self.connected = False

        # _log.info('Waiting for threads to finish')
        # self.thread_poll_report.join()
        # self.thread_receiver.join()
        # self.thread_send_gcode.join() # hangs on queue.get()

        self.ser.close()

    def get_config(self, timeout=2):
        self.requested_config = True
        self.serial_send('$$')
        start_time = time.time()
        while self.requested_config and time.time()-start_time < timeout:
            time.sleep(0.2)
        print('received full config: ', self.machine.grbl_config)

    def soft_reset(self):
        while not self.lines_to_sent.empty():
            self.lines_to_sent.get()
        while not self.chars_in_buffer.empty():
            self.chars_in_buffer.get()
        self.serial_send(COMMANDS['soft reset'])
        self.terminal.clear_buffers()

    def serial_send(self, line, blocking=False, queue_count=0):
        '''
        Send a string over the serial connection to grbl. If the line is an
        alarm or report request, it is send directly. Use blocking to wait
        until the line is send.
        '''
        if not self.connected:
            return False

        # 'extended ascii' commands
        if type(line) == int:
            byte = struct.pack('>B', line)
            self.ser.write(byte)
            return True
        # real-time commands do not wait in buffer, so they are send directly
        elif line in ('!', '?', '~'):
            self.ser.write(line.encode('ascii'))
        # if line is gcode etc. add it to the send queue
        else:
            self.terminal.store_send(line)
            self.lines_to_sent.put(line)
            line_nr = self.lines_count + len(self.lines_to_sent.queue)
            if blocking:
                while self.lines_count < (line_nr - queue_count):
                    time.sleep(0.001)
        return True

    def _gcode_sender(self):
        while not self._quit:
            line = self.lines_to_sent.get()
            # _log.info(f'sending a command -> "{line}"')

            while (sum(self.chars_in_buffer.queue)+len(line)+1 >=
                    (config['RX_BUFFER_SIZE']-1)):
                # other thread is handling the incomming messages
                # all we have to do, is wait for the buffer to be handled
                time.sleep(0.001)

            # Send g-code block to grbl
            self.ser.write((line + '\n').encode('ascii'))

            # Track number of characters in grbl serial read buffer
            self.chars_in_buffer.put(len(line)+1)
            self.lines_count += 1

            self.terminal.send_to_buffer()

    def _request_state(self):
        ''' Periodicly send '?' to request a new state. '''
        while not self._quit:
            self.serial_send('?')
            time.sleep(1/config['POLL_STATE_FREQ'])

    def _receive_continuously(self):
        # Continuously reads the serial buffer and does the required actions.
        buffer = bytearray()
        while not self._quit:
            i = buffer.find(b"\n")
            if i >= 0:
                # handle a line
                line = buffer[:i+1]
                buffer = buffer[i+1:]
                s = line.decode('ascii').strip()
                if s:
                    self._handle_received(s)
            else:
                # read more lines
                waiting = max(1, min(2048, self.ser.in_waiting))
                buffer.extend(self.ser.read(waiting))

    def _handle_received(self, out_temp):
        # if 'ok' or 'error' (finished a command from the buffer):
        if ('ok' in out_temp) or ('error' in out_temp):
            self.chars_in_buffer.get()

            if ('error' in out_temp):
                self.terminal.received_ok(error=True)
                self.terminal.store_received(out_temp, error=True)
            else:
                self.terminal.received_ok()

        # if it is a report message (for machine state manager):
        elif (out_temp[0] == '<' and out_temp[-1] == '>'):
            self.machine.handle_grbl_report(out_temp)

        elif (('ALARM' in out_temp) or ('Hold' in out_temp)
                or ('Door' in out_temp)):
            _log.debug(f'Message received "{out_temp}"')
            self.terminal.store_received(out_temp, error=True)

        # if it is a message without ok or error (like after $$)
        else:
            if self.requested_config:
                if out_temp[0] == '$':
                    item, value = out_temp.split('=')
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                    self.machine.grbl_config[item] = value
                    if item == '$132':  # last item
                        self.requested_config = False
            else:
                _log.debug(f'Message received "{out_temp}"')
                self.terminal.store_received(out_temp)
