
# dependencies
from threading import Thread
import logging

# kivy imports
from kivy.clock import mainthread
from kivy.properties import BooleanProperty

# submodules
from laserinterface.ui.themedwidgets import ShadedBoxLayout

_log = logging.getLogger().getChild(__name__)


class TerminalDisplay(ShadedBoxLayout):
    show_verbose = BooleanProperty(True)

    def set_datamanager(self, machine=None, terminal=None, grbl_com=None):
        self.terminal_man = terminal or self.terminal_man
        self.grbl_com = grbl_com or self.grbl_com

        if self.terminal_man:
            self.terminal_man.add_callback(self.update_terminal)

    def set_verbose(self, active):
        self.show_verbose = active
        self.update_terminal()

    @mainthread
    def update_terminal(self):
        lines = self.terminal_man.get_all_lines(verbose=self.show_verbose)
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
        Thread(target=self.grbl_com.serial_send, args=(command,)).start()


if __name__ == '__main__':
    from kivy.app import App  # noqa
    from kivy.lang import Builder  # noqa
    from os.path import join, dirname  # noqa

    filename = join(dirname(__file__), 'kv', 'terminaldisplay.kv')
    kv_file = Builder.load_file(filename)

    class TestApp(App):
        def build(self):
            return TerminalDisplay()

    TestApp().run()
