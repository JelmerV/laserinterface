# dependencies
import logging

_log = logging.getLogger().getChild(__name__)


class MachineStateManager():
    def __init__(self):
        self.grbl_config = {}
        self.grbl_status = {'WCO': [.0, .0, .0]}
        self.gpio_status = {}
        self.cooling_temp = 99

        self.grbl_callbacks = []
        self.temp_callbacks = []
        self.gpio_callbacks = []

    def add_grbl_callback(self, callback):
        if callable(callback):
            self.grbl_callbacks.append(callback)
            callback(self.grbl_status)
        return callable(callback)

    def handle_grbl_report(self, state_in):
        state_items = state_in[1:-1].split('|')  # remove < > and split
        self.grbl_status['state'] = state_items.pop(0)
        for item in state_items:
            try:
                name, value = item.split(':')
                if name not in ('A', 'Pn'):
                    value = value.split(',')
                    value = [float(i) for i in value]
                self.grbl_status[name] = value

                if 'MPos' in self.grbl_status.keys():
                    mpos = self.grbl_status['MPos']
                    wco = self.grbl_status['WCO']
                    wpos = [mpos[0]-wco[0], mpos[1]-wco[1]]
                    self.grbl_status['WPos'] = wpos
                elif 'WPos' in self.grbl_status.keys():
                    wpos = self.grbl_status['WPos']
                    wco = self.grbl_status['WCO']
                    mpos = [mpos[0]+wco[0], mpos[1]+wco[1]]
                    self.grbl_status['MPos'] = mpos

            except ValueError:
                _log.warning(f'received a corrupt status report {state_in}')

        if self.grbl_callbacks:
            for callback in self.grbl_callbacks:
                callback(self.grbl_status)

    def add_temp_callback(self, callback):
        if callable(callback):
            self.temp_callbacks.append(callback)
            callback(self.cooling_temp)
        return callable(callback)

    def update_temp(self, temp):
        self.cooling_temp = temp
        if self.temp_callbacks:
            for callback in self.temp_callbacks:
                callback(temp)

    def add_gpio_callback(self, callback):
        if callable(callback):
            self.gpio_callbacks.append(callback)
            for item, state in self.gpio_status.items():
                callback(item, state)

        return callable(callback)

    def update_gpio(self, item, new_state):
        _log.debug(f'gpio "{item}" changed -> "{new_state}", start callbacks')
        self.gpio_status[item] = new_state
        if self.gpio_callbacks:
            for callback in self.gpio_callbacks:
                callback(item, new_state)
