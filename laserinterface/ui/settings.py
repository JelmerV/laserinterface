
# dependencies
import logging
import ruamel.yaml
import serial
import serial.tools.list_ports

# kivy imports
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.popup import Popup

_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile, )['GRBL']
print([comport.device for comport in serial.tools.list_ports.comports()])


class ConnectGrbl(Popup):
    grbl_com = ObjectProperty()
    ports_dropdown = ObjectProperty()
    connect_state = StringProperty('Select the port of the arduino/grbl.')

    def on_open(self):
        self.prev_ports = []
        self.update_portlist()
        self.update_event = Clock.schedule_interval(self.update_portlist, 0.5)
        return super().on_dismiss()

    def on_dismiss(self):
        if self.update_event:
            self.update_event.cancel()
        return super().on_dismiss()

    def update_portlist(self, dt=0):
        portlist = self.get_ports()
        if portlist != self.prev_ports:
            self.ids.ports_dropdown.clear_widgets()
            for port in portlist:
                btn = Button(
                    text=str(port),
                    size_hint_y=None,
                    height=30
                )
                btn.bind(
                    on_release=lambda btn: self.select_port(btn.text))
                self.ids.ports_dropdown.add_widget(btn)

        return True

    def get_ports(self):
        port_list = []
        for comport in serial.tools.list_ports.comports():
            port_list.append(comport.device)
        if len(port_list) <= 0:
            port_list = ['<None available>']
        return port_list

    def select_port(self, port):
        port = str(port)
        print(port, 'selected')
        if port == '<None available>':
            return False

        self.ids.port_btn.text = port
        self.ids.ports_dropdown.dismiss()

        self.connect_state = 'trying to connect to '+port
        if not self.grbl_com.set_port(port):
            self.grbl_com.connect()

        if self.grbl_com.connected:
            self.connect_state = 'connected succesful'
            with open(config_file, 'r') as ymlfile:
                full_config = yaml.load(ymlfile)
            full_config['GRBL']['PORT'] = port
            with open(config_file, 'w') as ymlfile:
                yaml.dump(full_config, ymlfile)
        else:
            self.connect_state = 'Connection failed'


if __name__ == '__main__':
    from kivy.app import App  # noqa
    from kivy.lang import Builder  # noqa
    from os.path import join, dirname  # noqa

    filename = join(dirname(__file__), 'kv', 'settings.kv')
    kv_file = Builder.load_file(filename)

    class TestApp(App):
        def build(self):
            return ConnectGrbl()

    TestApp().run()
