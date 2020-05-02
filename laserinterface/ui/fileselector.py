
# dependencies
from threading import Thread
import logging
import ruamel.yaml

# Kivy imports
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout

# submodules
from laserinterface.helpers.gcodereader import GcodeReader, MOVE_TYPE


_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    base_dir = yaml.load(ymlfile)['GENERAL']['GCODE_DIR']


class FileSelector(BoxLayout):
    selected_file = StringProperty('')
    base_dir = StringProperty(base_dir)

    valid_gcode_selected = False

    def on_file_selected(self, filename='', *args, **kwarg):
        # if hasattr(self, 'painter'):
        #     self.ids.plotted_preview.continue_painting = False
        #     self.painter.join()
        #     self.ids.plotted_preview.continue_painting = True
        print(filename)

        if not filename:
            self.gcode_text = '(Please select a valid file)'
            return
        self.selected_file = filename
        app = App.get_running_app()
        app.root.ids.home.ids.job_control.selected_file = filename

        try:
            with open(self.selected_file) as gcode_file:
                gcode_text = [l.strip() for l in gcode_file.readlines(1000)]
            self.valid_gcode_selected = True
        except UnicodeDecodeError:
            gcode_text = ["Could not read the file. No valid gcode.",
                          'Please select a ".nc", ".gcode", or ".txt" file']
            self.valid_gcode_selected = False
        except FileNotFoundError:
            # selected a folder?
            return

        # show part of the text in a recycleview
        data = []
        for nr in range(len(gcode_text)):
            data.append({
                'line_nr': nr,
                'gcode': gcode_text[nr],
            })
        self.ids.gcode_preview.data = data

        self.painter = Thread(target=self.ids.plotted_preview.draw_gcode_file,
                              args=(filename,))
        self.painter.start()


class PlottedGcode(RelativeLayout):
    ''' Scatter widget (dragable) placed inside a StencilView. dragging
    function overriden to prevent scolling past the borders of the workspace.
    Also provides functions to draw paths on the canvas of the Scatter. '''

    max_x = NumericProperty(0.00)
    max_y = NumericProperty(0.00)
    min_x = NumericProperty(0.00)
    min_y = NumericProperty(0.00)

    job_duration = NumericProperty(0.00)

    def __init__(self, **kwargs):
        super(PlottedGcode, self).__init__(**kwargs)
        print('PlottedGcode init function called!')
        self.continue_painting = True

        self.reader = GcodeReader()
        self.paths = []

        # Clock.schedule_once(
        #     lambda dt: self.draw_workspace(width=110, height=80), 1)
        self.draw_workspace(width=110, height=80)

    def draw_workspace(self, scale=1, width=300, height=300, spacing=100):
        print('redrawing workspace grid')
        self.canvas.remove_group('workspace')
        with self.canvas:
            # outline and middle line
            Color(0.90, 0.90, 0.90)
            Line(width=3, group='workspace',
                 point=(0, 0, 30, 30))
            Line(width=3, group='workspace',
                 point=(-width/2, 0,
                        width/2,  0))
            Line(width=3, group='workspace',
                 point=(0, -height/2,
                        0, height/2))
            Line(width=3, group='workspace',
                 point=(-width/2, -height/2,
                        -width/2, height/2,
                        width/2, height/2,
                        width/2, -height/2,
                        -width/2, -height/2))
            Color(0.60, 0.60, 0.60)
            Line(points=(), width=3, group='workspace',
                 dash_length=4, dash_offset=2)

    def draw_gcode_file(self, filename):
        def set_label(text):
            self.ids.plottedgcode_label.text = text

        Clock.schedule_once(lambda dt: set_label('Calculating path...'), 0)

        self.draw_workspace()
        _log.info(f'Calculating paths of {filename}')
        self.paths = self.reader.handle_file(filename)
        self.max_x = self.reader.max_x
        self.max_y = self.reader.max_y
        self.min_x = self.reader.min_x
        self.min_y = self.reader.min_y
        self.job_duration = self.reader.job_duration

        Clock.schedule_once(lambda dt: set_label('Drawing path...'), 0)
        self.draw_paths(self.paths)

        Clock.schedule_once(lambda dt: set_label(''), 0)

    def draw_paths(self, paths):
        if len(paths) < 1:
            return

        size_x = -self.min_x + self.max_x
        size_y = -self.min_y + self.max_y
        scale_factor = min(self.width/size_x, self.height/size_y)

        self.canvas.remove_group('gcode')
        with self.canvas:
            Color(0.90, 0.90, 0.90)
            Line(width=1, group='workspace', points=(
                0, (-self.min_y)*scale_factor,
                self.width,  (-self.min_y)*scale_factor))
            Line(width=1, group='workspace', points=(
                (-self.min_x)*scale_factor, 0,
                (-self.min_x)*scale_factor, self.height))
            Line(width=1, group='workspace', dash_length=2, dash_offset=1,
                 points=(
                     0, (self.max_y-self.min_y) * scale_factor,
                     self.width, (self.max_y-self.min_y)*scale_factor))
            Line(width=1, group='workspace', dash_length=2, dash_offset=1,
                 points=(
                     (self.max_x-self.min_x) * scale_factor, 0,
                     (self.max_x-self.min_x) * scale_factor, self.height))
            self.ids.max_x_label.x = min(
                size_x*scale_factor, self.width-self.ids.max_x_label.width)
            self.ids.max_y_label.y = min(
                size_y*scale_factor, self.height-self.ids.max_x_label.height)

            for path in paths:
                if not self.continue_painting:
                    self.continue_painting = True
                    return

                w = 1.3 if path.laser_on else 0.5
                # set color and line style depending on the movement type
                if path.move_type == MOVE_TYPE['RAPID']:
                    Color(0.8, 0.415, 0.886)
                    line = Line(points=(), width=w, group='gcode')
                elif path.move_type == MOVE_TYPE['LINEAR']:
                    Color(0.415, 0.886, 0.717)
                    line = Line(points=(), width=w, group='gcode')
                elif (path.move_type == MOVE_TYPE['ARC_CW'] or
                        path.move_type == MOVE_TYPE['ARC_CCW']):
                    Color(0.415, 0.623, 0.886)
                    line = Line(points=(), width=w, group='gcode')

                for i in range(len(path.points_x)):
                    scaled_point = (
                        (path.points_x[i]-self.min_x)*scale_factor,
                        (path.points_y[i]-self.min_y)*scale_factor,
                    )
                    line.points.extend(scaled_point)

            self.do_layout()
