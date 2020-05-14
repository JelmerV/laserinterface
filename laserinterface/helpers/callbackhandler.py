import logging
import ruamel.yaml

from laserinterface.data.grbl_doc import COMMANDS

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile)


class CallbackHandler:
    def __init__(self, grbl, gpio):
        self.grbl = grbl
        self.gpio = gpio

    def do_callback(self, event):
        # Callbacks can be configured in the config.yaml in this format:
        # events/rules:
        #   {OUT/IN}_{PIN_NAME/ANY}_{ON/OFF/ANY}
        #   TEMP_{RED/ORANGE/GREEN}
        #   JOB_{START/STOP/PAUSE}
        # actions:
        #   OUT_{NAME}: {ON/OFF/EQUAL/OPPOSITE}
        #   SEND_GRBL: {HOLD/CONTINUE}

        # type = {OUT/IN} or TEMP or JOB
        # name = {PIN_NAME/ANY} or {RED/ORANGE/GREEN} or {START/STOP/PAUSE}
        # event = {ON/OFF/ANY} or None

        event = event.upper()
        _log.info(f'Callback started for {event}')

        event_type, event_name = event.split('_', 1)
        if event_type not in ('TEMP', 'JOB'):
            event_name, event_state = event_name.rsplit('_', 1)

        # GPIO
        for rule, actions in config['CALLBACKS'].items():
            rule_type, rule_name = rule.upper().strip().split('_', 1)

            activate = False
            if rule_type in ('TEMP', 'JOB'):
                activate = (rule == event)
            else:      # GPIO rules
                rule_name, rule_state = rule_name.rsplit('_', 1)
                activate = bool(
                    (rule_type == event_type) and
                    ((rule_name == 'ANY') or (rule_name == event_name)) and
                    ((rule_state == 'ANY') or (rule_state == event_state))
                )

            if activate:
                _log.info(f'"{event}" triggered "{actions}"')
                for action_name, action_state in actions.items():
                    # trigger GPIO actions
                    if action_name.startswith('OUT'):
                        if action_state == 'ON':
                            self.gpio.pin_write(action_name, True)
                        elif action_state == 'OFF':
                            self.gpio.pin_write(action_name, False)
                        elif action_state == 'EQUAL':
                            new_state = True if event_state == 'ON' else False
                            self.gpio.pin_write(action_name, new_state)
                        elif action_state == 'OPPOSITE':
                            new_state = True if event_state == 'OFF' else False
                            self.gpio.pin_write(action_name, new_state)
                        else:
                            _log.warning(
                                f'action state: {action_state} not recognized')

                    # GRBL commands
                    if action_name == 'SEND_GRBL':
                        if action_state == 'HOLD':
                            self.grbl.serial_send(COMMANDS['feed hold'])
                        elif action_state == 'RESUME':
                            self.grbl.serial_send(COMMANDS['cycle resume'])
                        else:
                            _log.warning(
                                f'action state: {action_state} not recognized')
