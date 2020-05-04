
# kivy imports
from kivy.clock import mainthread
from kivy.graphics import Line, Color
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.relativelayout import RelativeLayout


class MachineView(RelativeLayout):
    state = StringProperty()
    mpos = StringProperty()
    wpos = StringProperty()

    grid_size = NumericProperty(100)

    def set_datamanager(self, machine=None, terminal=None, grbl_com=None):
        self.machine_state = machine

        if self.machine_state:
            self.machine_state.add_state_callback(self.update_state)

        # Clock.schedule_once(lambda dt:
        self.draw_workspace()  # , 0)

    def draw_workspace(self, spacing=100):
        self.grid_size = spacing or self.grid_size
        try:
            width = float(self.machine_state.grbl_config['$130'])
            height = float(self.machine_state.grbl_config['$131'])
        except (AttributeError, KeyError):
            width = 500.0
            height = 300.0
        scale = min(self.width/width, self.height/height)
        self.scale = scale

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
        self.mpos = f"({status['MPos'][0]:.2f}, {status['MPos'][0]:.2f})"
        self.wpos = f"({status['WCO'][0]:.2f}, {status['WCO'][0]:.2f})"

        # move the marker. homing position is the top
        self.ids.mach_mark.center_x = status['MPos'][0]*self.scale
        self.ids.mach_mark.center_y = status['MPos'][1]*self.scale+self.height

        self.ids.zero_mark.center_x = status['WCO'][0]*self.scale
        self.ids.zero_mark.center_y = status['WCO'][1]*self.scale + self.height
