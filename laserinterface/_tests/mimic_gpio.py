from threading import Thread
from time import sleep
import random


class GPIO_mimic:
    ''' Class to mimic the rpi.gpio module '''

    def __init__(self, random_inputs=True):
        self.val = {}
        self.state = {}
        self.BOARD = 0
        self.IN = 1
        self.OUT = 0

        if random_inputs:
            input_modifier = Thread(target=self.__change_inputs, daemon=True)
            input_modifier.start()

    def __change_inputs(self):
        sleep(2)
        while True:
            for item in self.state.keys():
                if self.state[item] == self.IN:
                    self.val[item] = random.choice([True, False])
                sleep(0.5)
            sleep(3)

    def checkModeValidator(self):
        pass

    def setmode(self, mode):
        pass

    def setwarnings(self, flag):
        pass

    def setup(self, channel, state, initial=False, pull_up_down=-1):
        self.state[channel] = state
        self.val[channel] = initial

    def output(self, channel, outmode):
        self.val[channel] = outmode

    def input(self, channel):
        if(self.state[channel] == self.OUT):
            return self.val[channel]
        if(self.state[channel] == self.IN):
            return self.val[channel]

    def cleanup(self):
        pass
