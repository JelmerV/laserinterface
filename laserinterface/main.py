
# external dependencies
import os
import sys
import logging
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.properties import ObjectProperty

# Helping submodules
from laserinterface.datamanager.machine import MachineStateManager
from laserinterface.datamanager.terminal import TerminalManager
from laserinterface.helpers.gpiointerface import GpioInterface
from laserinterface.helpers.grblinterface import GrblInterface
from laserinterface.helpers.gcodereader import GcodeReader
from laserinterface.helpers.callbackhandler import CallbackHandler

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
    kv_directory = os.path.join(os.path.dirname(__file__), 'ui/kv')

    # shared datamanagers
    terminal = ObjectProperty()
    machine = ObjectProperty()

    # shared helpers
    grbl = ObjectProperty()
    gpio = ObjectProperty()
    gcode = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # initialize datamanagers
        self.terminal = TerminalManager()
        self.machine = MachineStateManager()

        # initialize backend helpers
        self.grbl = GrblInterface(machine=self.machine, terminal=self.terminal)
        self.gpio = GpioInterface(machine=self.machine)
        self.gcode = GcodeReader()

        self.callback = CallbackHandler(grbl=self.grbl, gpio=self.gpio)
        self.gpio.callback = self.callback

        Clock.schedule_once(
            lambda dt: self.gpio.pin_write('OUT_LIGHT', True), 2)
        Clock.schedule_once(
            lambda dt: self.gpio.pin_write('OUT_COOLING', True), 2)

    def build(self):
        return MainLayout()

    def restart_program(self):
        _log.warning('closing grbl connections and stopping threads')
        self.grbl.disconnect()
        _log.warning('Stopping gpio threads')
        self.gpio.close()

        _log.warning('Stopping kivy application')
        self.stop()

        os.execl(sys.executable, f'"{sys.executable}"', *sys.argv)

    def reboot_controller(self):
        _log.warning('closing grbl connections and stopping threads')
        self.grbl.disconnect()
        _log.warning('Stopping gpio threads')
        self.gpio.close()

        _log.warning('Stopping kivy application')
        self.stop()

        _log.warning('rebooting the controller ("sudo reboot")')
        # os.system('sudo reboot')

    def poweroff_controller(self):
        _log.warning('closing grbl connections and stopping threads')
        self.grbl.disconnect()
        _log.warning('Stopping gpio threads')
        self.gpio.close()

        _log.warning('Stopping kivy application')
        self.stop()

        _log.warning('powering off the controller ("sudo poweroff")')
        # os.system('sudo poweroff')


def main():
    print('starting LaserInterface')
    laserinterface_app = MainLayoutApp()
    laserinterface_app.run()


if __name__ == '__main__':
    main()
