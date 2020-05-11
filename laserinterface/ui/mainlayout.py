
# dependencies
import logging
import os
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy import resources
from kivy.clock import Clock
from kivy.properties import NumericProperty
from kivy.uix.floatlayout import FloatLayout


from laserinterface.ui.fileselector import FileSelector, PlottedGcode
from laserinterface.ui.gpiodisplay import GpioInputIcons, GpioInputLabels
from laserinterface.ui.gpiodisplay import GpioOutputController, GpioCallbacks
from laserinterface.ui.jobcontroller import JobController
from laserinterface.ui.jogmachine import Jogger
from laserinterface.ui.machineview import MachineView
from laserinterface.ui.settings import ConnectGrbl, GrblConfig
from laserinterface.ui.terminaldisplay import TerminalDisplay

_log = logging.getLogger().getChild(__name__)

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
print(data_dir)
resources.resource_add_path(data_dir)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    grbl_buffer_size = yaml.load(ymlfile)['GRBL']['RX_BUFFER_SIZE']


# main layout with topbar and screenmanager
class MainLayout(FloatLayout):
    grbl_buffer = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio

        self.grblconfig = GrblConfig()
        self.grblconfig.grbl = self.grbl

        self.connectgrbl = ConnectGrbl()
        self.connectgrbl.grbl = self.grbl

        if not self.grbl.connect():
            Clock.schedule_once(self.connectgrbl.open, 0)

        Clock.schedule_interval(self.update_properties, 0.05)

    def open_grblconnect(self):
        self.connectgrbl.open()

    def open_grblconfig(self):
        self.grblconfig.open()

    def update_properties(self, dt):
        self.grbl_buffer = sum(self.grbl.chars_in_buffer.queue)
