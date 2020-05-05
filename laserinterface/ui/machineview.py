
# kivy imports
from kivy.app import App
from kivy.clock import mainthread
from kivy.graphics import Line, Color
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.relativelayout import RelativeLayout


class MachineView(RelativeLayout):
    state = StringProperty()
    wco = StringProperty()
    wpos = StringProperty()

    grid_size = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio

        self.machine.add_state_callback(self.update_state)

    def draw_workspace(self, spacing=100):
        try:
            width = float(self.machine.grbl_config['$130'])
            height = float(self.machine.grbl_config['$131'])
        except (AttributeError, KeyError):
            width = 500.0
            height = 300.0
        scale = min(self.width/width, self.height/height)
        self.scale = scale

        # find nearest power for a suitable spacing
        spacing = min([5, 10, 20, 50, 100, 200], key=lambda x: abs(x-width/10))
        self.grid_size = spacing

        self.canvas.remove_group('workspace')
        with self.canvas:
            Color(0.60, 0.60, 0.60)
            for i in range(int(width/spacing)):
                Line(width=0.5, group='workspace',
                     points=(i*spacing*scale, 0,
                             i*spacing*scale, height*scale))
            for i in range(int(height/spacing)):
                Line(width=0.5, group='workspace',
                     points=(0, self.height-i*spacing*scale,
                             width*scale, self.height-i*spacing*scale))

    @mainthread
    def update_state(self, status):
        self.state = status['state']
        self.wpos = f"({status['WPos'][0]:.2f}, {status['WPos'][1]:.2f})"
        self.wco = f"({status['WCO'][0]:.2f}, {status['WCO'][1]:.2f})"

        # move the marker. homing position is the top
        self.ids.wpos_mark.center_x = status['MPos'][0]*self.scale
        self.ids.wpos_mark.center_y = status['MPos'][1]*self.scale+self.height

        self.ids.wco_mark.center_x = status['WCO'][0]*self.scale
        self.ids.wco_mark.center_y = status['WCO'][1]*self.scale+self.height
