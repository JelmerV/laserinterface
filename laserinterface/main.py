
# external dependencies
from os.path import join, dirname
import logging
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window

# import main module for ui
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

    def build(self):
        self.main_layout = MainLayout()
        return self.main_layout

    def on_start(self):
        Clock.schedule_once(self.main_layout.initialize, 0)

    def restart_program(self):
        # if systemctl is set up correctly the ar should restar automaticly
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
