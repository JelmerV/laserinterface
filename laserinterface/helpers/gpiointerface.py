
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
    mimic_gpio = config['GENERAL']['MIMIC_GPIO_LIB']
    mimic_gpio_change = config['GENERAL']['MIMIC_GPIO_CHANGE']
    config = config['GPIO']

if mimic_gpio:
    _log.error(' Will be mimicing the functions!')
    from laserinterface._tests.mimic_gpio import GPIO_mimic  # noqa
    GPIO = GPIO_mimic(random_inputs=mimic_gpio_change)
else:
    from RPi import GPIO  # noqa


class GpioInterface(Thread):
    def __init__(self, machine, auto_start=True):
        Thread.__init__(self)
        self.daemon = True

        self.machine = machine  # is a datamanager object
        self.callback = None

        self._quit = False

        self.last_update_time = 0

        GPIO.setmode(getattr(GPIO, config['PINTYPE']))
        for name, dic in config['INPUTS'].items():
            GPIO.setup(dic['PIN'], GPIO.IN)
            self.machine.update_gpio(f'IN_{name}', GPIO.input(dic['PIN']))
            # self.on_change(f'IN_{name}', GPIO.input(dic['PIN']))
        for name, pin_nr in config['OUTPUTS'].items():
            GPIO.setup(pin_nr, GPIO.OUT, initial=True)
            self.machine.update_gpio(f'OUT_{name}', False)
            # self.on_change(f'OUT_{name}', False)

        if auto_start:
            self.start()

    def pin_write(self, item, next_value=False):
        if self.machine.gpio_status[item] == next_value:
            # nothing changing
            return

        item = item[4:]

        # if next_value is '!' toggle the output
        if (next_value == '!'):
            next_value = not self.machine.gpio_status['OUT_'+item]

        GPIO.output(config['OUTPUTS'][item], not next_value)
        self.on_change(f'OUT_{item}', next_value)

        _log.info('toggling ' + item + '. next value is ' + str(next_value))
        return next_value

    def on_change(self, item, new_state):
        self.machine.update_gpio(item, new_state)
        self.callback.do_callback(f'{item}_{"ON" if new_state else "OFF"}')

    def close(self):
        self._quit = True
        GPIO.cleanup()

    def run(self):
        ''' Function runs when Thread.start() is called '''
        _log.info(f'starting polling loop. frequency is {config["POLL_FREQ"]}')

        temp_thread = Thread(target=self.temp_thread, daemon=True)
        temp_thread.start()

        while not self._quit:
            # get gpio inputs
            for name, dic in config['INPUTS'].items():
                new_state = not GPIO.input(dic['PIN'])
                if self.machine.gpio_status[f'IN_{name}'] != new_state:
                    self.on_change(f'IN_{name}', new_state)

            time.sleep(1/config['POLL_FREQ'])

    def temp_thread(self):
        if mimic_gpio:
            if not mimic_gpio_change:
                return
            temp_c = 20
            up = 1
            last_state = ''
            while not self._quit:
                if temp_c >= 25 or temp_c <= 17:
                    up = -up
                temp_c += up/4
                self.machine.update_temp(temp_c)
                time.sleep(0.2)
                # TEMP
                if temp_c >= config['TEMP_RANGE']['RED']:
                    state = 'RED'
                elif temp_c >= config['TEMP_RANGE']['ORANGE']:
                    state = 'ORANGE'
                else:
                    state = 'GREEN'

                self.machine.update_temp(temp_c)
                if state != last_state:
                    self.callback.do_callback(f'TEMP_{state}')
                    last_state = state
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

        last_state = ''
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

            # TEMP
            if temp_c >= config['TEMP_RANGE']['RED']:
                state = 'RED'
            elif temp_c >= config['TEMP_RANGE']['ORANGE']:
                state = 'ORANGE'
            else:
                state = 'GREEN'

            self.machine.update_temp(temp_c)
            if state != last_state:
                self.callback.do_callback(f'TEMP_{state}')
                last_state = state

        return
