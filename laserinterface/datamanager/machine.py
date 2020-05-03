import logging
_log = logging.getLogger().getChild(__name__)


class MachineStateManager():

    def __init__(self):

        self.grbl_status = {}
        self.gpio_status = {}
        self.cooling_temp = 99

        self.warning_callbacks = []
        self.state_callbacks = []
        self.temp_callbacks = []
        self.gpio_callbacks = []

    def add_gpio_callback(self, callback):
        '''
        Callbacks added here will be called whenever the gpio state is changed.
        the changed item and its new value will be added as an argument to the
        callback funtion.
        '''
        if callable(callback):
            _log.info('new gpio callback is being registered; '+str(callback))
            self.gpio_callbacks.append(callback)
        else:
            _log.warning(f'new gpio callback "{callback}" is not callable!')
        return callable(callback)

    def update_gpio(self, item, new_state):
        _log.debug(f'gpio "{item}" changed -> "{new_state}", start callbacks')
        self.gpio_status[item] = new_state
        if self.gpio_callbacks:
            for callback in self.gpio_callbacks:
                callback(item, new_state)

    def add_temp_callback(self, callback):
        '''
        Callbacks added here will be called whenever the tempereture of the
        cooling water is changed. The new temperature will be given as an
        argument in the callback funtion.
        '''
        if callable(callback):
            self.temp_callbacks.append(callback)
        return callable(callback)

    def update_temp(self, temp):
        self.cooling_temp = temp
        if self.temp_callbacks:
            for callback in self.temp_callbacks:
                callback(temp)

    def add_state_callback(self, callback):
        '''
        Callbacks added here will be called whenever a new report from grbl is
        handled. The reports is stored as a dict, and this dict will be added
        as an argument for the callback function.
        '''
        if callable(callback):
            self.state_callbacks.append(callback)
        return callable(callback)

    def handle_grbl_report(self, state_in):
        state_items = state_in[1:-1].split('|')  # remove < > and split
        self.grbl_status['state'] = state_items.pop(0)
        raw = {}
        for item in state_items:
            name, value = item.split(':')
            raw[name] = value
            self.grbl_status[name] = value
        # self.grbl_status['mach_pos'] =

        if self.state_callbacks:
            for callback in self.state_callbacks:
                callback(self.grbl_status)

    def add_warning_callback(self, callback):
        if callable(callback):
            self.warning_callbacks.append(callback)
        return callable(callback)

    def _warning_callback(self):
        print('warning activated, calling the warning callbacks')
        if self.warning_callbacks:
            for callback in self.warning_callbacks:
                print(f'calling {callback}')
                # callback()
