
# dependencies
from threading import Thread
from os import path
import logging
import time
import re
import ruamel.yaml

# kivy imports
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.properties import BooleanProperty
from kivy.properties import BoundedNumericProperty
from kivy.properties import NumericProperty
from kivy.properties import StringProperty
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup

# Submodules
from laserinterface.data.grbl_doc import COMMANDS
from laserinterface.ui.themedwidgets import ShadedBoxLayout

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile)


class JobController(ShadedBoxLayout):
    power_override = BoundedNumericProperty(
        100, min=10, max=200,
        errorhandler=lambda x: 200 if x > 200 else 10)
    feed_override = BoundedNumericProperty(
        100, min=10, max=200,
        errorhandler=lambda x: 200 if x > 200 else 10)
    repeat_count = BoundedNumericProperty(
        100, min=1, max=10,
        errorhandler=lambda x: 10 if x > 10 else 1)

    actual_feed = NumericProperty(-1)
    actual_power = NumericProperty(-1)

    selected_file = StringProperty('<Please select a file>')
    job_active = BooleanProperty(False)
    job_duration = NumericProperty(0)
    job_progress = BoundedNumericProperty(100)

    paused = False
    stop_sending_job = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio
        self.callback = app.callback
        self.not_zero_popup = NotAtZeroPopup(self)

        self.machine.add_grbl_callback(self.update_state)

    def set_zero(self):
        self.grbl.serial_send('G92 X0 Y0 Z0')

    def start_here(self):
        # called to start a job while not at the zero position
        self.start_job(ignore_zero=True)

    def start_job(self, ignore_zero=False):
        app = App.get_running_app()

        if self.selected_file == '<Please select a file>':
            app.root.ids.sm.current = 'job'
            return

        # check if at the configured 0 pos
        mpos = self.machine.grbl_status['MPos']
        wco = self.machine.grbl_status['WCO']
        tol = 0.1
        at_zero = abs(mpos[0]-wco[0]) <= tol and abs(mpos[1]-wco[1]) <= tol
        if not ignore_zero and not at_zero:
            self.not_zero_popup.open()
            return

        self.callback.do_callback('JOB_START')

        _log.info('starting job '+self.selected_file)
        self.job_thread = Thread(target=self.send_full_file, daemon=True)
        self.job_thread.start()

        app.root.job_active = True
        self.job_active = True

    def pause_job(self):
        if self.paused:
            self.grbl.serial_send(COMMANDS['cycle resume'])
            self.paused = False
            self.ids.pause_button.text = 'Pause'

            self.callback.do_callback('JOB_START')
        else:
            self.grbl.serial_send(COMMANDS['feed hold'])
            self.paused = True
            self.ids.pause_button.text = 'Continue'
            self.callback.do_callback('JOB_PAUSE')

    def stop_job(self):
        # first reset to immediately halt the machine
        self.stop_sending_job = True
        self.grbl.serial_send('M5')

    def send_full_file(self):
        def update_progress(dt):
            self.job_duration = int(time.time() - start_time)
            self.job_progress = int(count*100.0/total_lines/self.repeat_count)

        def finish_job(dt):
            self.callback.do_callback('JOB_STOP')
            _log.info('Finished sending a file.')
            self.job_progress = 100
            app.root.job_active = False
            self.job_active = False

        total_lines = 1
        count = 0

        app = App.get_running_app()
        start_time = time.time()
        timer = Clock.schedule_interval(update_progress, 0.1)

        # keep only the first x numbers of a decimal
        trim_nr = config['GENERAL']['TRIM_DECIMALS_TO']
        re_decimals = re.compile(r'(\w[+-]?\d+\.\d{'+str(trim_nr)+r'})\d+')
        # spaces and comments (**) and ;**
        re_comments = re.compile(r'\((.*?)\)|;(.*)')
        re_redundant = re.compile(r'\+|\s|\(.*?\)|;.*')

        _path = path.join(config['GENERAL']['GCODE_DIR'], self.selected_file)
        with open(_path, 'r') as file:
            lines = file.readlines()

        total_lines = len(lines)
        repeats = 0
        while repeats < self.repeat_count:
            repeats += 1
            for line in lines:
                if self.stop_sending_job:
                    timer.cancel()
                    Clock.schedule_once(finish_job, 0)
                    self.stop_sending_job = False
                    return

                line = line.strip().upper()

                # trim decimals:
                if trim_nr:
                    line = re_decimals.sub(r'\1', line)

                # store comments to terminal, then strip them
                comments = re_comments.search(line)
                if comments:
                    self.terminal.store_comment(comments.group(0))
                line = re_redundant.sub('', line)

                if line == '':
                    continue

                # send line but wait if buffer is full, do queue three extra
                self.grbl.serial_send(line, blocking=True, queue_count=3)
                count += 1

        # wait until all lines are received
        while len(self.terminal.line_wait_for_ok) > 0:
            time.sleep(0.1)

        timer.cancel()
        Clock.schedule_once(finish_job, 0)

    def override_power(self, command):
        gcode = 0
        if command == '-10':
            gcode = COMMANDS['power -10']
            self.power_override -= 10
        elif command == '-1':
            gcode = COMMANDS['power -1']
            self.power_override -= 1
        elif command == 'reset':
            gcode = COMMANDS['power reset']
            self.power_override = 100
        elif command == '+1':
            gcode = COMMANDS['power +1']
            self.power_override += 1
        elif command == '+10':
            gcode = COMMANDS['power +10']
            self.power_override += 10

        if gcode:
            Thread(target=self.grbl.serial_send, args=(gcode,)).start()

    def override_feed(self, command):
        gcode = 0
        if command == '-10':
            gcode = COMMANDS['feed -10']
            self.feed_override -= 10
        elif command == '-1':
            gcode = COMMANDS['feed -1']
            self.feed_override -= 1
        elif command == 'reset':
            gcode = COMMANDS['feed reset']
            self.feed_override = 100
        elif command == '+1':
            gcode = COMMANDS['feed +1']
            self.feed_override += 1
        elif command == '+10':
            gcode = COMMANDS['feed +10']
            self.feed_override += 10

        if gcode:
            Thread(target=self.grbl.serial_send, args=(gcode,)).start()

    @mainthread
    def update_state(self, status):
        if not status.get('state'):
            return
        if status['state'] == 'Idle' and self.job_active:
            print('gcode is not being send fast enough!!')

        fs = status.get('FS')
        if fs:
            self.actual_feed = fs[0]
            self.actual_power = fs[1]
        else:
            self.actual_feed = status.get('FS')
            self.actual_power = -1


class NotAtZeroPopup(Popup):
    JobController = ObjectProperty()

    def __init__(self, job_control, **kwargs):
        super().__init__(**kwargs)
        self.job_control = job_control
