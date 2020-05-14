# dependencies
import logging
import ruamel.yaml

# kivy imports
from kivy.clock import Clock

# submodules
from laserinterface.ui.themedwidgets import ShadedBoxLayout

_log = logging.getLogger(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile)


class CallbackDisplay(ShadedBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: self.setup(), 0)

    def setup(self):
        data = []
        for event, actions in config['CALLBACKS'].items():
            name, new_value = event.rsplit('_', 1)
            event = f"When '{name}' switches to '{new_value}' do:"

            acts = []
            for output, next_val in actions.items():
                acts.append(f"Switch '{output}' to be '{next_val}'")
            actions = '\n'.join(acts)

            data.append({
                'event': event,
                'action': actions,
            })

        self.ids.rv.data = data
