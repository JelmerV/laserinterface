
# external dependencies
from os.path import join, dirname
import logging
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.properties import ObjectProperty

# Helping submodules
from laserinterface.datamanager.machine import MachineStateManager
from laserinterface.datamanager.terminal import TerminalManager
from laserinterface.helpers.gpiointerface import GpioInterface
from laserinterface.helpers.grblinterface import GrblInterface

# import all modules for the ui
from laserinterface.ui.mainlayout import MainLayout

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    do_fullscreen = yaml.load(ymlfile)['GENERAL']['FULLSCREEN']

if do_fullscreen:
    Window.fullscreen = True
else:
    Config.set('graphics', 'width', '1024')
    Config.set('graphics', 'height', '600')


class MainLayoutApp(App):
    kv_directory = join(dirname(__file__), 'ui/kv')

    terminal = ObjectProperty()
    machine = ObjectProperty()
    grbl = ObjectProperty()
    gpio = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # initialize datamanagers
        self.terminal = TerminalManager()
        self.machine = MachineStateManager()

        # initialize backend helpers
        self.grbl = GrblInterface(machine=self.machine, terminal=self.terminal)
        self.gpio = GpioInterface(machine=self.machine)

    def build(self):
        return MainLayout()

    def restart_program(self):
        # if systemctl is set up correctly the ar should restar automaticly
        _log.warning('closing connections and stopping threads')
        self.grbl.disconnect()
        self.gpio.close()

        self.stop()

    def reboot_controller(self):
        _log.warning('rebooting the controller ("sudo reboot")')
        # os.system('sudo reboot')

    def poweroff_controller(self):
        _log.warning('powering off the controller ("sudo poweroff")')
        # os.system('sudo poweroff')


def main():
    print('starting LaserInterface')
    laserinterface_app = MainLayoutApp()
    laserinterface_app.run()


if __name__ == '__main__':
    main()
