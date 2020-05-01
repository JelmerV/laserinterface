
# dependencies
import logging
import os
import ruamel.yaml

# kivy imports
from kivy import resources
from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty

# kivy widgets
from kivy.uix.floatlayout import FloatLayout

# Helping submodules
from laserinterface.datamanager.machine import MachineStateManager
from laserinterface.datamanager.terminal import TerminalManager
from laserinterface.helpers.gpiointerface import GpioInterface
from laserinterface.helpers.grblinterface import GrblInterface

# Widget submodules. Most are only used at the kv side, but import is needed
from laserinterface.ui.fileselector import FileSelector
from laserinterface.ui.gcodeplotter import GcodeReader, PlottedGcode
from laserinterface.ui.gpiodisplay import GpioInputIcons
from laserinterface.ui.jobcontroller import JobController
from laserinterface.ui.jogmachine import Jogger
from laserinterface.ui.machinestate import MachineState
from laserinterface.ui.machineview import MachineView
from laserinterface.ui.settings import ConnectGrbl
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
    job_active = BooleanProperty(False)
    job_duration = NumericProperty(0)
    grbl_buffer = NumericProperty(0)

    def initialize(self, *args):
        # initialize datamanagers
        self.terminal = TerminalManager()
        self.state = MachineStateManager()

        # initialize backend helpers
        self.grbl_com = GrblInterface(
            terminal=self.terminal,
            machine_state=self.state
        )
        self.gpio = GpioInterface(
            machine_state=self.state
        )
        self.pass_objects()

        self.connectgrbl = ConnectGrbl()
        self.connectgrbl.grbl_com = self.grbl_com
        if not self.grbl_com.connect():
            self.connectgrbl.open()

        Clock.schedule_interval(self.update_propperties, 0.02)

    def pass_objects(self):
        self.ids.gpio_display.set_datamanager(
            machine=self.state)

        self.ids.home.ids.terminal_display.set_datamanager(
            terminal=self.terminal, grbl_com=self.grbl_com)
        self.ids.home.ids.machine_view.set_datamanager(
            machine=self.state, grbl_com=self.grbl_com)
        self.ids.home.ids.job_control.set_datamanager(
            machine=self.state, grbl_com=self.grbl_com)

        self.ids.move.ids.terminal_display.set_datamanager(
            terminal=self.terminal, grbl_com=self.grbl_com)
        self.ids.move.ids.machine_view.set_datamanager(
            machine=self.state)
        self.ids.move.ids.jog_controller.set_datamanager(
            terminal=self.terminal, machine=self.state, grbl_com=self.grbl_com)

        self.ids.gpio.ids.inputs.set_datamanager(
            machine=self.state)
        self.ids.gpio.ids.outputs.set_datamanager(
            machine=self.state, gpio_con=self.gpio)

    def open_grblconnect(self):
        self.connectgrbl.open()

    def update_propperties(self, dt):
        self.grbl_buffer = sum(self.grbl_com.chars_in_buffer.queue)
        if self.job_active and self.grbl_buffer < 10:
            print('*'*90, self.grbl_buffer)
