# External Dependencies
from threading import Thread
import time
import serial
import re
import struct
import ruamel.yaml
import queue

# Setup logging
import logging
_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile, )['GRBL']


class GrblInterface:
    def __init__(self, terminal=None, machine_state=None, buffer_val=None):
        # Store or Create terminal and state instance
        self.terminal = terminal
        self.state = machine_state

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
        ''' Connect to the configured serial port.
        connects and sends new lines to wake up grbl. Then it starts the thread
        to handle any receided data, and starts an addition thread to
        periodicly request the machine state. '''

        _log.info(f'connecting to {self.ser.port}')
        try:
            self.ser.open()
        except serial.SerialException:
            _log.info(f'Failed to connect to {self.ser.port}')
            self.connected = False
            return False

        self.connected = True
        time.sleep(0.5)
        self.ser.write('\r\n\r\n'.encode('utf-8'))

        self.thread_receiver = Thread(
            target=self._receive_continuously, daemon=True)
        self.thread_receiver.start()

        self.thread_poll_report = Thread(
            target=self._request_state, daemon=True)
        self.thread_poll_report.start()

        self.thread_send_gcode = Thread(target=self._gcode_sender, daemon=True)
        self.thread_send_gcode.start()

        return True

    def disconnect(self):
        ''' set flag to stop the threads, then close the connection '''
        self._quit = True
        self.connected = False

        _log.info('Waiting for threads to finish')
        self.thread_poll_report.join()
        self.thread_receiver.join()

        self.ser.close()

    def serial_send(self, line_in, blocking=False):
        ''' Send a string over the serial connection to grbl.
        If the line is an alarm or report request, it is send directly. Strings
        are send withhout the gcode comments and with a newline. Sending is
        done with a blocking method. Run in a thread to prevent that'''
        if not self.connected:
            return False

        if type(line_in) == int:
            byte = struct.pack('>B', line_in)
            self.ser.write(byte)
            return True

        comments = re.search(r'\((.+?)\)|;.+', line_in.strip())
        if comments:
            comment = comments.group(0)
            self.terminal.store_comment(comment)
            _log.info('comment in gcode found -> '+comment)

        # Strip spaces and comments (**) and ;**
        line = re.sub(r'\s|\(.*?\)|;(.*)', '', line_in)
        line = line.upper().strip()

        # if line has no gcode, dont send it
        if line == '':
            return True
        elif line in ('!', '?', '~'):
            self.ser.write(line.encode('ascii'))
        # if line is gcode, send using the send function
        else:
            self.terminal.store_send(line)
            self.lines_to_sent.put(line)
            line_nr = self.lines_count + len(self.lines_to_sent.queue)
            if blocking:
                while self.lines_count < line_nr:
                    time.sleep(0.001)
            _log.debug('line send -> '+line)
        return True

    def _gcode_sender(self):
        while not self._quit:
            line = self.lines_to_sent.get()
            _log.info(f'sending a command -> "{line}"')

            # or self.ser.inWaiting()
            while (sum(self.chars_in_buffer.queue)+len(line) >=
                    (config['RX_BUFFER_SIZE']-2)):
                # other thread is handling the incomming messages
                # all we have to do, is wait for the buffer to be handled
                time.sleep(0.001)

            # Send g-code block to grbl
            _log.info(f'starting to send line')
            self.ser.write((line + '\n').encode('ascii'))

            # Track number of characters in grbl serial read buffer
            self.chars_in_buffer.put(len(line)+1)
            self.lines_count += 1

            self.terminal.send_to_buffer()
            _log.info(f'line send succesful')

    def _request_state(self):
        ''' Periodicly send '?' to request a new state. '''
        while not self._quit:
            self.serial_send('?')
            time.sleep(1/config['POLL_STATE_FREQ'])

    def _receive_continuously(self):
        ''' Continuously checks if there is data available in the serial buffer.
        It data is available it calls the handling function. '''

        while not self._quit:
            while self.ser.inWaiting():
                self._handle_response()
            time.sleep(0.01)

    def _handle_response(self):
        ''' Reads a line from the serial buffer and does the required actions.
        status reports are send to the machine state class, 'ok' or 'error'
        messages mean the buffer and teminal variables have to be updates.1`w
        Other messages are added to the terminal history and can be displayed
        in the GUI. '''

        out_temp = self.ser.readline().decode('ascii')
        out_temp = out_temp.strip()

        if out_temp:
            # if it is a report message (machine state):
            if (out_temp[0] == '<' and out_temp[-1] == '>'):
                self.state.handle_grbl_report(out_temp)

            # if it is 'ok' or 'error' (finished a command from the buffer):
            elif ('ok' in out_temp) or ('error' in out_temp):
                if not self.chars_in_buffer.empty():
                    # Delete the block corresponding to the last 'ok'
                    self.chars_in_buffer.get()

                if ('error' in out_temp):
                    self.terminal.received_ok(error=True)
                    self.terminal.store_received(out_temp, error=True)
                else:
                    self.terminal.received_ok()

            elif (('ALARM' in out_temp) or ('Hold' in out_temp)
                    or ('Door' in out_temp)):
                _log.debug(f'Message received "{out_temp}"')
                self.terminal.store_received(out_temp, error=True)

            # if it is a message without ok or error (like after $$)
            else:
                _log.debug(f'Message received "{out_temp}"')
                self.terminal.store_received(out_temp)
