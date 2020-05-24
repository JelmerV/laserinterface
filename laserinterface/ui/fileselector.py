
# dependencies
from glob import glob
from subprocess import check_output
from threading import Thread
import logging
import os
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

    def __init__(self, **kw):
        super().__init__(**kw)
        app = App.get_running_app()
        self.reader = app.gcode

        # Clock.schedule_interval(self.find_usb, 1)

    def on_file_selected(self, selection):
        if not selection:
            return

        app = App.get_running_app()
        self.selected_file = os.path.relpath(selection[0], base_dir)
        app.root.ids.home.ids.job_control.selected_file = self.selected_file

        file_path = os.path.join(base_dir, self.selected_file)
        try:
            with open(file_path, 'r') as gcode_file:
                # read a 1000 bytes for a preview
                gcode_text = [l.strip() for l in gcode_file.readlines(1000)]
                gcode_text.append('...')
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
        self.ids.plotted_preview.selected_file = file_path

    def clear_mem(self):
        self.reader.reset()
        self.ids.plotted_preview.canvas.remove_group('gcode')
        self.ids.plotted_preview.plotted_file = ''

    def find_usb(self):
        if os.name == 'nt':
            return

        # get devices
        sdb_devices = map(os.path.realpath, glob('/sys/block/sd*'))
        usb_devices = (dev for dev in sdb_devices
                       if 'usb' in dev.split('/')[5])
        devices = dict((os.path.basename(dev), dev) for dev in usb_devices)

        # get mount points
        output = check_output(['mount']).splitlines()
        def is_usb(path): return any(dev in path for dev in devices)
        usb_info = (line for line in output if is_usb(line.split()[0]))
        print([(info.split()[0], info.split()[2]) for info in usb_info])

        # create hardlink
        for info in usb_info:
            mnt_point = info.mnt_point
            os.link(mnt_point, os.path.join(
                base_dir, os.path.basename(mnt_point)))


class PlottedGcode(RelativeLayout):
    max_x = NumericProperty(0.00)
    max_y = NumericProperty(0.00)
    min_x = NumericProperty(0.00)
    min_y = NumericProperty(0.00)

    grid_size = NumericProperty(0.00)

    job_duration = NumericProperty(0.00)
    selected_file = StringProperty()
    plotted_file = StringProperty()

    def __init__(self, **kw):
        super().__init__(**kw)
        self.paths = []

        app = App.get_running_app()
        self.reader = app.gcode

    def do_painting(self):
        self.painter = Thread(target=self.draw_gcode_file)
        self.painter.start()
        self.plotted_file = self.selected_file

    def draw_gcode_file(self):
        def set_label(text):
            self.ids.plottedgcode_label.text = text

        Clock.schedule_once(lambda dt: set_label('Calculating path...'), 0)

        filename = self.selected_file
        _log.info(f'Calculating paths of {filename}')
        self.paths = self.reader.handle_file(filename)
        self.max_x = self.reader.max_x
        self.max_y = self.reader.max_y
        self.min_x = self.reader.min_x
        self.min_y = self.reader.min_y
        self.job_duration = self.reader.job_duration

        Clock.schedule_once(lambda dt: set_label('Drawing path...'), 0)
        if self.paths:
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
