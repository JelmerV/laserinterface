
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
    full_report = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = App.get_running_app()

        self.terminal = app.terminal
        self.machine = app.machine
        self.grbl = app.grbl
        self.gpio = app.gpio
        self.gcode = app.gcode

        self.machine.add_grbl_callback(self.update_state)
        self.gcode.add_new_job_callback(self.update_gcode)

    def draw_workspace(self, spacing=100):
        try:
            self.grid_width = float(self.machine.grbl_config['$130'])
            height = float(self.machine.grbl_config['$131'])
        except (AttributeError, KeyError):
            self.grid_width = 500.0
            height = 300.0
        scale = min(self.width/self.grid_width, self.height/height)
        self.scale = scale

        # find nearest power for a suitable spacing
        spacing = min([1, 2, 5, 10, 20, 50, 100, 200],
                      key=lambda x: abs(x-self.grid_width/10))
        self.grid_size = spacing

        self.canvas.remove_group('workspace')
        with self.canvas:
            Color(0.60, 0.60, 0.60)
            for i in range(int(self.grid_width/spacing)):
                Line(width=0.5, group='workspace',
                     points=(i*spacing*scale, 0,
                             i*spacing*scale, height*scale))
            for i in range(int(height/spacing)):
                Line(width=0.5, group='workspace', points=(
                    0, self.height-i*spacing*scale,
                    self.grid_width*scale, self.height-i*spacing*scale))

    @mainthread
    def update_state(self, status):
        if not status.get('state'):
            return
        self.full_report = status
        self.state = status['state']
        self.wpos = f"({status['WPos'][0]:.2f}, {status['WPos'][1]:.2f})"
        old_wco = self.wco
        self.wco = f"({status['WCO'][0]:.2f}, {status['WCO'][1]:.2f})"

        # move the marker. homing position is the top
        self.ids.wpos_mark.center_x = (
            (status['MPos'][0]+self.grid_width)*self.scale)
        self.ids.wpos_mark.center_y = status['MPos'][1]*self.scale+self.height

        self.ids.wco_mark.center_x = (
            (status['WCO'][0]+self.grid_width)*self.scale)
        self.ids.wco_mark.center_y = status['WCO'][1]*self.scale+self.height

        if old_wco != self.wco:
            self.update_gcode()

    @mainthread
    def update_gcode(self):
        if not self.full_report.get('WCO'):
            return False

        max_x = self.gcode.max_x
        min_x = self.gcode.min_x
        max_y = self.gcode.max_y
        min_y = self.gcode.min_y
        wco_x = self.full_report['WCO'][0]
        wco_y = self.full_report['WCO'][1]

        # coordinate offsets
        ox = self.grid_width
        oy = self.height/self.scale

        self.canvas.remove_group('gcode')
        with self.canvas:
            # draw max, min lines and place labels
            Color(0.20, 0.80, 0.90)
            Line(width=0.9, group='gcode', points=(
                (wco_x+min_x+ox)*self.scale, (wco_y+min_y+oy)*self.scale,
                (wco_x+max_x+ox)*self.scale, (wco_y+min_y+oy)*self.scale,
                (wco_x+max_x+ox)*self.scale, (wco_y+max_y+oy)*self.scale,
                (wco_x+min_x+ox)*self.scale, (wco_y+max_y+oy)*self.scale,
                (wco_x+min_x+ox)*self.scale, (wco_y+min_y+oy)*self.scale,
            ))
