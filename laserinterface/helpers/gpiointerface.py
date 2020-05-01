
# dependencies
from threading import Thread
import time
import os
import glob
import ruamel.yaml
import logging

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile)
    mimmic_gpio = config['GENERAL']['MIMMIC_GPIO_LIB']
    mimmic_gpio_change = config['GENERAL']['MIMMIC_GPIO_CHANGE']
    config = config['GPIO']

if mimmic_gpio:
    _log.error('Could not import RPi.GPIO. Will be mimmicing the functions!')
    from laserinterface._tests.mimmic_gpio import GPIO_mimmic  # noqa
    import random
    GPIO = GPIO_mimmic(random_inputs=mimmic_gpio_change)
else:
    from RPi import GPIO  # noqa


class GpioInterface(Thread):
    # frequency of checking the in and outputs.
    # Also affect reaction speed on warnings!
    POLL_FREQ = 200

    def __init__(self, machine_state, auto_start=True):
        Thread.__init__(self)
        self.daemon = True

        self.state = machine_state  # is a datamanager object

        self._quit = False

        self.last_update_time = 0
        self.input_values = {'temp': 99}
        self.output_values = {}
        self.warnings = set()

        GPIO.setmode(getattr(GPIO, config['PINTYPE']))
        for item in config['INPUTS'].keys():
            GPIO.setup(config['INPUTS'][item]['PIN'], GPIO.IN)
            self.input_values[item] = GPIO.input(config['INPUTS'][item]['PIN'])
        for item in config['OUTPUTS'].keys():
            GPIO.setup(config['OUTPUTS'][item], GPIO.OUT, initial=True)
            self.output_values[item] = False

        if auto_start:
            self.start()

    def pin_write(self, item, next_value=False):
        # if next_value is '!' toggle the output
        if (next_value == '!'):
            next_value = not self.output_values[item]

        if self.output_values[item] == next_value:
            # nothing changing
            return

        # switch something off
        if (not next_value):
            GPIO.output(config['OUTPUTS'][item], True)
            self.output_values[item] = False
            self.state.update_gpio('OUT_'+item, False)
        # switch something on
        else:
            if (item == 'laser'):
                _log.info('activating laser.'
                          'also activates cooling and air assist')
                # when laser is turned on, also
                # enable air assist and water cooling
                self.pin_write('cooling', True)
                self.pin_write('air', True)
                # then enable laser power
                GPIO.output(config['OUTPUTS']['laser'], False)
                self.output_values['laser'] = True
                self.state.update_gpio('OUT_LASER', False)
            else:
                GPIO.output(config['OUTPUTS'][item], False)
                self.output_values[item] = True
                self.state.update_gpio('OUT_'+item, True)

        _log.info('toggling ' + item + '. next value is ' + str(next_value))
        return next_value

    def warning_callback(self):
        # called whenever a pin gets low
        self.pin_write('GRBL', False)
        self.pin_write('LASER', False)
        time.sleep(0.1)
        self.pin_write('MOTOR', False)

    def close(self):
        self._quit = True
        GPIO.cleanup()

    def run(self):
        '''Function runs when Thread.start() is called'''
        _log.info("starting polling loop. frequency is "+str(self.POLL_FREQ))

        temp_thread = Thread(target=self.temp_thread, daemon=True)
        temp_thread.start()

        temp_limit = float(config['TEMP_RANGE']['RED'])

        next_time = time.time()
        while not self._quit:
            # clear active warnings
            last_warnings = self.warnings.copy()
            self.warnings.clear()

            # get gpio inputs
            for item in config['INPUTS'].keys():
                new_state = not GPIO.input(config['INPUTS'][item]['PIN'])
                if not new_state:
                    self.warnings.add(item)
                if self.input_values[item] != new_state:
                    self.input_values[item] = new_state
                    self.state.update_gpio('IN_'+item, self.input_values[item])

            if (self.input_values['temp'] >= temp_limit):
                self.warnings.add('temp')

            # handle active warnings
            if (len(self.warnings) > 0) and (self.warnings != last_warnings):
                _log.warning("Warnings activated -> "+str(self.warnings))
                self.warning_callback()

            next_time += 1/config['POLL_FREQ']
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                # print('polling gpio reruns in:', sleep_time, 'secs')
                time.sleep(sleep_time)

    def temp_thread(self):
        if mimmic_gpio:
            temp_c = 17
            up = True
            while not self._quit:
                if up:
                    if temp_c >= 25:
                        up = not up
                    temp_c += random.uniform(-0.05, 0.4)
                else:
                    if temp_c <= 19:
                        up = not up
                    temp_c -= random.uniform(-0.05, 0.4)

                self.state.update_temp(temp_c)
                self.input_values['temp'] = temp_c
                time.sleep(0.1)
            return

        # find file url for the ds18b20 readings
        thermometer_url = ""
        while not thermometer_url:
            try:
                os.system('modprobe w1-gpio')
                os.system('modprobe w1-therm')
                device_folder = glob.glob('/sys/bus/w1/devices/28*')[0]
                thermometer_url = device_folder + '/w1_slave'
                _log.info("Found temperature file -> "+thermometer_url)
            except IndexError:
                thermometer_url = None

        while not self._quit:
            temp_c = 99

            # get laser tube temperature
            with open(thermometer_url, 'r') as f:
                lines = f.readlines()
            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.1)
                with open(thermometer_url, 'r') as f:
                    lines = f.readlines()

            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                temp_c = float(temp_string) / 1000.0

            self.input_values['temp'] = temp_c
            self.state.update_temp(temp_c)

        return
