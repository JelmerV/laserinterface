
# dependencies
from threading import Thread
import logging
import time

# kivy imports
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.properties import BoundedNumericProperty
from kivy.properties import NumericProperty
from kivy.properties import StringProperty

# Submodules
from laserinterface.data.grbl_doc import COMMANDS
from laserinterface.ui.themedwidgets import ShadedBoxLayout

_log = logging.getLogger().getChild(__name__)


class JobController(ShadedBoxLayout):
    power_override = BoundedNumericProperty(
        100, min=10, max=200,
        errorhandler=lambda x: 200 if x > 200 else 10)
    feed_override = BoundedNumericProperty(
        100, min=10, max=200,
        errorhandler=lambda x: 200 if x > 200 else 10)
    job_progress = BoundedNumericProperty(100)

    selected_file = StringProperty('<Please select a file>')
    job_active = BooleanProperty(False)
    job_duration = NumericProperty(0)

    def set_datamanager(self, machine=None, terminal=None, grbl_com=None):
        self.grbl_com = grbl_com or self.grbl_com

    def start_job(self):
        app = App.get_running_app()

        if self.selected_file == '<Please select a file>':
            app.root.ids.sm.current = 'job'
            return

        _log.info('starting job '+self.selected_file)
        self.job_thread = Thread(target=self.send_full_file, daemon=True)
        self.job_thread.start()

        app.root.job_active = True
        self.job_active = True

    def send_full_file(self):
        app = App.get_running_app()
        start_time = time.time()

        with open(self.selected_file, 'r') as file:
            lines = file.readlines()

        total_lines = len(lines)
        count = 0
        last_progress = 0
        for line in lines:
            self.grbl_com.serial_send(line, blocking=True)

            self.job_duration = int(time.time() - start_time)

            progress = int(count*100.0/total_lines)
            if progress > last_progress:
                Clock.schedule_once(
                    lambda dt: self.setter('job_progress')(self, progress), 0)
            last_progress = progress
            count += 1

        def finish_job(dt):
            _log.info('Finished sending a file.')
            self.job_progress = 100
            app.root.job_active = False
            self.job_active = False

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
            Thread(target=self.grbl_com.serial_send, args=(gcode,)).start()

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
            Thread(target=self.grbl_com.serial_send, args=(gcode,)).start()


# kv_file = Builder.load_file('jobcontrol.kv')
if __name__ == '__main__':
    class TestApp(App):
        def build(self):
            return JobController()

    TestApp().run()
