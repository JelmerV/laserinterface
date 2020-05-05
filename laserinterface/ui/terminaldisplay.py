
# dependencies
import logging

# kivy imports
from kivy.app import App
from kivy.clock import mainthread, Clock
from kivy.properties import BooleanProperty

# submodules
from laserinterface.ui.themedwidgets import ShadedBoxLayout

_log = logging.getLogger().getChild(__name__)


class TerminalDisplay(ShadedBoxLayout):
    show_verbose = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio

        self.terminal.add_callback(self.update_terminal)
        Clock.schedule_once(lambda dt: self.show_last(), 3)

    def set_verbose(self, active):
        self.show_verbose = active
        self.update_terminal()

    @mainthread
    def update_terminal(self):
        lines = self.terminal.get_all_lines(verbose=self.show_verbose)
        data = []
        for line in lines:
            dic = {
                'id': str(line[0]),
                'line_nr': line[0],
                'state': line[1],
                'text': line[2],
            }
            data.append(dic)

        self.ids.terminal_display.data = data

    def send_command(self):
        command = self.ids.command_input.text
        _log.info('sending command from the textinput -> '+command)
        self.grbl.serial_send(command)

    def show_last(self):
        self.ids.terminal_display.scroll_y = 0
