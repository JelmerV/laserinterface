from laserinterface.data.grbl_doc import ERROR_CODES, CONFIG

import logging
_log = logging.getLogger().getChild(__name__)


STATES = {
    'cancel':     '! Cancelled',
    'comment':    '! Comment: ',
    'send_wait':  '|>    [...]',
    'send_buf':   '|-->  [BUF]',
    'send_ok':    '|-->  [OK ]',
    'send_err':   '|-->  [ERR]',
    'recv_err':   '|<--  [ERR]',
    'recv_msg':   '|<--  [MSG]',
}


class TerminalManager():
    def __init__(self, history_count=500):
        # TerminalManager keeps track of the lines in sendbuffers and history
        # and offers the function to format them.
        # each line is stored as a list with the following items:
        #  - linenumber: int
        #  - state:      str
        #  - line:       str

        self.history_count = history_count      #: line count stored in history
        self.callbacks = []
        self.clear_all()

    def clear_all(self):
        self.line_out_buffer = []      #: lines to be send (grbl buffer full)
        self.line_wait_for_ok = []     #: lines send and in grbl buffer
        self.line_history = []         #: lines send and handled
        self.comments = []           #: comments stored from program or gcode

        self.line_number = 0
        self.line_number_error = 0

    def clear_buffers(self):
        while len(self.line_out_buffer) > 0:
            line = self.line_out_buffer.pop(0)
            line[1] = STATES['cancel']
            self.line_history.append(line)

        while len(self.line_wait_for_ok) > 0:
            line = self.line_wait_for_ok.pop(0)
            line[1] = STATES['cancel']
            self.line_history.append(line)

    def add_callback(self, callback):
        if callable(callback):
            self.callbacks.append(callback)
        return callable(callback)

    def get_all_lines(self, verbose=True):
        # combine all to a single list
        if verbose:
            lines = [
                *self.line_history,
                *self.line_wait_for_ok,
                *self.line_out_buffer,
                *self.comments,
            ]
        else:
            msg = []
            for line in self.line_history:
                if (line[1] == STATES['recv_msg'] or
                        line[1] == STATES['recv_err'] or
                        line[1] == STATES['comment']):
                    msg.append(line)
            lines = [
                *msg,
                *self.comments,
            ]
        # sort by linenumber and return
        return sorted(lines, key=lambda x: x[0])

    def callback(self):
        # All callbacks are called every time a line is modified
        if self.callbacks:
            for callback in self.callbacks:
                callback()

    def store_comment(self, comment):
        line = [self.line_number, STATES['comment'], comment]
        self.line_number += 1
        _log.debug(f'stored a comment -> ' + str(line))
        self.line_history.append(line)

        self.callback()

    def store_received(self, line, error=False):
        if error:
            state = STATES['recv_err']
            line_nr = self.line_number_error
            line = ERROR_CODES.get(line, line)
        else:
            if line[0] == '$':
                line += f"    ({CONFIG.get(line.split('=')[0])})"
            state = STATES['recv_msg']
            line_nr = self.line_number
            self.line_number += 1
        line = [line_nr, state, line]
        _log.debug(f'Added line to history -> ' + str(line))
        self.line_history.append(line)

        self.callback()

    def received_ok(self, error=False):
        # line from grbl buffer was handled. move to history
        # try:
        #     line = self.line_wait_for_ok.pop(0)
        # except IndexError:
        #     _log.error('error while popping line from list')
        #     return False

        try:
            line = self.line_wait_for_ok.pop(0)
        except IndexError:
            _log.error('"ok" or "error" received but the send buffer was '
                       'already empty. Some send line has been missed by '
                       'the terminal manager.')

        if error:
            line[1] = STATES['send_err']
            self.line_number_error = line[0]
        else:
            line[1] = STATES['send_ok']
        self.line_history.append(line)
        lines_too_many = len(self.line_history)-self.history_count
        if lines_too_many > 0:
            # remove lines to prevent crossing max history count
            self.line_history = self.line_history[lines_too_many:]

        self.callback()
        return True

    def store_send(self, send_line):
        # send a line to grbl. Currently in Serial OUT buffer
        # when send succesfully, call send_succes()
        line = [self.line_number, STATES['send_wait'], send_line]
        self.line_number += 1
        self.line_out_buffer.append(line)

        self.callback()

    def send_to_buffer(self):
        # when a line is send from the output buffer and received at the buffer
        # of grbl. This function moves the line to the correct variables.
        try:
            line = self.line_out_buffer.pop(0)
        except IndexError:
            _log.error('A line switched from sending buffer to grbl buffer, '
                       'but the line_out_buffer was empty')

        line[1] = STATES['send_buf']
        self.line_wait_for_ok.append(line)

        self.callback()
