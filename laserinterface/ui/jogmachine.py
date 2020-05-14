
# dependencies
import logging
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy.properties import NumericProperty

# Submodules
from laserinterface.data.grbl_doc import COMMANDS
from laserinterface.ui.themedwidgets import ShadedBoxLayout


_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    pulse_dur = yaml.load(ymlfile, )['GENERAL']['LASER_PULSE_DURATION']


class Jogger(ShadedBoxLayout):
    stepsize_range = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
    feedrate_range = [100, 200, 500, 1000, 2000, 5000, 10000]

    stepsize = NumericProperty(stepsize_range[7])
    feedrate = NumericProperty(feedrate_range[5])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio

    def set_stepsize(self, val):
        val = int(val)
        self.stepsize = self.stepsize_range[val]

    def set_feedrate(self, val):
        val = int(val)
        self.feedrate = self.feedrate_range[val]

    def jog(self, command=''):
        command = command.upper()

        # add '$J='+ for interruptable jogging
        gcode = '$J='+'G91G21'
        if command == '-X+Y':
            gcode += f'X-{self.stepsize}Y{self.stepsize}'
        elif command == '+Y':
            gcode += f'Y{self.stepsize}'
        elif command == '+X+Y':
            gcode += f'X{self.stepsize}Y{self.stepsize}'
        elif command == '-X':
            gcode += f'X-{self.stepsize}'
        elif command == '+X':
            gcode += f'X{self.stepsize}'
        elif command == '-X-Y':
            gcode += f'X-{self.stepsize}Y-{self.stepsize}'
        elif command == '-Y':
            gcode += f'Y-{self.stepsize}'
        elif command == '+X-Y':
            gcode += f'X{self.stepsize}Y-{self.stepsize}'

        gcode += f'F{self.feedrate}'

        self.grbl.serial_send(gcode)
        return

    def stop_jog(self):
        self.grbl.serial_send(COMMANDS['cancel jog'])

    def go_to_zero(self):
        self.grbl.serial_send(f'$J=G90X0Y0F{self.feedrate}')

    def set_zero(self):
        self.grbl.serial_send('G92X0Y0')

    def rehome(self):
        self.grbl.serial_send(COMMANDS['start homing'])

    def unlock_alarm(self):
        self.grbl.serial_send(COMMANDS['kill alarm'])

    def reset_grbl(self):
        App.get_running_app().root.ids.home.ids.job_control.stop_job()
        self.grbl.soft_reset()

    def pulse_laser(self):
        ''' turns laser on for the configured period'''
        self.grbl.serial_send(f'M3G1S1000F{self.feedrate}G4P{pulse_dur}')
        self.grbl.serial_send('M5')
