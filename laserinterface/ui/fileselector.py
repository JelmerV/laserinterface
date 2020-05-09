
# dependencies
from threading import Thread
from os import path
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
from laserinterface.helpers.gcodereader import MOVE_TYPE


_log = logging.getLogger().getChild(__name__)

yaml = ruamel.yaml.YAML()
config_file = 'laserinterface/data/config.yaml'
with open(config_file, 'r') as ymlfile:
    base_dir = yaml.load(ymlfile)['GENERAL']['GCODE_DIR']


class FileSelector(BoxLayout):
    selected_file = StringProperty('')
    base_dir = StringProperty(base_dir)

    valid_gcode_selected = False

    def on_file_selected(self, selection):
        # if hasattr(self, 'painter'):
        #     self.ids.plotted_preview.continue_painting = False
        #     self.painter.join()
        #     self.ids.plotted_preview.continue_painting = True
        if not selection:
            return

        app = App.get_running_app()
        self.selected_file = path.relpath(selection[0], base_dir)
        app.root.ids.home.ids.job_control.selected_file = self.selected_file

        file_path = path.join(base_dir, self.selected_file)
        try:
            with open(file_path, 'r') as gcode_file:
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
                              args=(file_path,))
        self.painter.start()


class PlottedGcode(RelativeLayout):
    ''' Scatter widget (dragable) placed inside a StencilView. dragging
    function overriden to prevent scolling past the borders of the workspace.
    Also provides functions to draw paths on the canvas of the Scatter. '''

    max_x = NumericProperty(0.00)
    max_y = NumericProperty(0.00)
    min_x = NumericProperty(0.00)
    min_y = NumericProperty(0.00)

    grid_size = NumericProperty(0.00)

    job_duration = NumericProperty(0.00)

    def __init__(self, **kw):
        super().__init__(**kw)

        print('PlottedGcode init function called!')
        self.continue_painting = True
        self.paths = []

        app = App.get_running_app()
        self.reader = app.gcode

    def draw_gcode_file(self, filename):
        def set_label(text):
            self.ids.plottedgcode_label.text = text

        Clock.schedule_once(lambda dt: set_label('Calculating path...'), 0)

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

        min_x = self.min_x
        min_y = self.min_y
        max_x = self.max_x
        max_y = self.max_y
        size_x = -min_x + max_x
        size_y = -min_y + max_y
        scale = min(self.width/size_x, self.height/size_y)

        space_opt = [1, 2, 5, 10, 20, 50, 100, 200]
        spacing = min(space_opt, key=lambda x: abs(x-size_x/4))
        self.grid_size = spacing

        self.canvas.remove_group('gcode')
        self.canvas.remove_group('grid')
        with self.canvas:
            # draw max, min lines and place labels
            Color(0.90, 0.90, 0.90)
            Line(width=0.8, group='grid', points=(
                0, (-min_y)*scale,
                self.width,  (-min_y)*scale))
            Line(width=0.8, group='grid', points=(
                (-min_x)*scale, 0,
                (-min_x)*scale, self.height))
            Line(width=1, group='grid', points=(
                0, (max_y-min_y)*scale,
                (max_x-min_x)*scale, (max_y-min_y)*scale))
            Line(width=0.6, group='grid', points=(
                (max_x-min_x) * scale, 0,
                (max_x-min_x) * scale, (max_y-min_y)*scale))
            self.ids.max_x_label.x = min(
                size_x*scale, self.width-self.ids.max_x_label.width)
            self.ids.max_y_label.y = min(
                size_y*scale, self.height-self.ids.max_x_label.height)

            # draw grid:
            Color(0.30, 0.30, 0.30)
            for i in range(1, int(-min_x/spacing)+1):
                Line(width=0.3, group='grid', points=(
                     (-min_x-i*spacing)*scale, 0,
                     (-min_x-i*spacing)*scale, self.height))
            for i in range(1, int(self.width/scale/spacing)+1):
                Line(width=0.3, group='grid', points=(
                     (-min_x+i*spacing)*scale, 0,
                     (-min_x+i*spacing)*scale, self.height))
            for i in range(1, int(-min_y/spacing)+1):
                Line(width=0.3, group='grid', points=(
                     0,          (-min_y-i*spacing)*scale,
                     self.width, (-min_y-i*spacing)*scale))
            for i in range(1, int(self.height/scale/spacing)+1):
                Line(width=0.3, group='grid', points=(
                     0,          (-min_y+i*spacing)*scale,
                     self.width, (-min_y+i*spacing)*scale))

            # draw the paths of the gcode
            for _path in paths:
                if not self.continue_painting:
                    self.continue_painting = True
                    return

                w = 1.1 if _path.laser_on else 0.5
                # set color and line style depending on the movement type
                if _path.move_type == MOVE_TYPE['RAPID']:
                    Color(0.8, 0.415, 0.886)
                    line = Line(points=(), width=w, group='gcode')
                elif _path.move_type == MOVE_TYPE['LINEAR']:
                    Color(0.415, 0.886, 0.717)
                    line = Line(points=(), width=w, group='gcode')
                elif (_path.move_type == MOVE_TYPE['ARC_CW'] or
                        _path.move_type == MOVE_TYPE['ARC_CCW']):
                    Color(0.415, 0.623, 0.886)
                    line = Line(points=(), width=w, group='gcode')

                for i in range(len(_path.points_x)):
                    scaled_point = (
                        (_path.points_x[i]-min_x)*scale,
                        (_path.points_y[i]-min_y)*scale,
                    )
                    line.points.extend(scaled_point)

            self.do_layout()
