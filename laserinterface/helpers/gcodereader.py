
# Dependencies
from dataclasses import dataclass, field
import logging
import math
import re
import sys

_log = logging.getLogger().getChild(__name__)

# Constants values
INCH = 25.4    # mm per inch

# Constants for movement types
MOVE_TYPE = {
    'RAPID': 0,
    'LINEAR': 1,
    'ARC_CW': 2,
    'ARC_CCW': 3,
}


@dataclass
class Path:
    ''' A path object contains the type and the positions of a movement '''
    points_x: list = field(default_factory=list)
    points_y: list = field(default_factory=list)
    move_type: int = 0      # Type of a move (rapid, linear, arc cw or ccw)
    laser_on: bool = False  # laser powered on (M3, M4) of off (M5) on path
    start_line: int = 0     # Linenumber of gcode command where the move starts
    end_line: int = 0       # Linenumber of gcode command where the move ended


class GcodeReader:
    new_job_callbacks = []
    complete_paths = []
    current_path = Path([0], [0])

    unit_factor = 1.0
    absolute_steps = True

    job_duration = 0.0

    max_x = 0.0
    max_y = 0.0
    min_x = 0.0
    min_y = 0.0

    def __init__(self):
        self.reset()

    def reset(self):
        self.complete_paths = []
        self.current_path = Path([0], [0])

        self.job_duration = 0
        self.feed_rate = 1000
        self.max_x = 0
        self.max_y = 0
        self.min_x = 0
        self.min_y = 0

    def add_new_job_callback(self, callback):
        if callable(callback):
            self.new_job_callbacks.append(callback)
        return callable(callback)

    def handle_file(self, filename) -> list:
        ''' Read all lines in a file and call the handling function
        returns list of paths'''

        _log.info(f'gcode reader starting to handle {filename}')
        try:
            self.reset()
            with open(filename) as f:
                for line_number, fullString in enumerate(f):
                    # strip comments
                    fullString = re.sub(r'\(.*?\)|;.*', '', fullString)
                    fullString = fullString.upper().strip()

                    # skip lines without commands
                    if fullString == '':
                        continue

                    # split lines containing multiple commands
                    listOfLines = fullString.split('G')
                    if len(listOfLines) > 1:  # if multiple commands found
                        for line in listOfLines:
                            if len(line) > 0:  # If the line is not blank
                                self._handle_command('G'+line, line_number)
                                line_number += 1
                    else:
                        self._handle_command(fullString, line_number)
                        line_number += 1

            for callback in self.new_job_callbacks:
                callback()
            print(f'Complete list of paths takes up for {filename}'
                  f' {sys.getsizeof(self.complete_paths)} bytes')
            return self.complete_paths

        except UnicodeDecodeError:
            _log.info(f'{filename} can not be decoded as text')
            return

    def _handle_command(self, command, line_number=0):
        ''' Check the command and call the path handling functions, or set the
        related variables. If the command is different from the last, then it
        moves the path to completed_paths, and creates a new one. '''

        # Ensures the first 3 chars are only the G command
        # if len(command) > 2 and not command[2].isdigit():
        #     command = command[:2] + ' ' + command[2:]
        params = {}
        # _log.debug(f'starting to handle command -> {command}')

        configuration_command = True
        # Configuration commands
        if command.startswith('G20'):
            self.unit_factor = 1.0/INCH
        elif command.startswith('G21'):
            self.unit_factor = 1.0
        elif command.startswith('G90'):
            self.absolute_steps = True
        elif command.startswith('G91'):
            self.absolute_steps = False
        else:
            configuration_command = False

        if configuration_command:
            return

        # Movement commands
        if command.startswith(('G00', 'G0')):
            params['move_type'] = MOVE_TYPE['RAPID']
        elif command.startswith(('G01', 'G1')):
            params['move_type'] = MOVE_TYPE['LINEAR']
        elif command.startswith(('G02', 'G2')):
            params['move_type'] = MOVE_TYPE['ARC_CW']
        elif command.startswith(('G03', 'G3')):
            params['move_type'] = MOVE_TYPE['ARC_CCW']
        elif command.startswith('G'):
            print('No recognized movement type', command)
            return
        else:
            params['move_type'] = self.current_path.move_type

        # Switching laser on or off
        if command.startswith(('M03', 'M3', 'M04', 'M4')):
            params['laser_on'] = True
        elif command.startswith(('M05', 'M5')):
            params['laser_on'] = False
        else:
            params['laser_on'] = self.current_path.laser_on

        # switch to a new path?
        if (self.current_path.move_type != params['move_type']
                or self.current_path.laser_on != params['laser_on']):
            _log.debug(f'command changed. making new Path()')
            # commands changed: create new path
            params['points_x'] = [self.current_path.points_x[-1]]
            params['points_y'] = [self.current_path.points_y[-1]]
            params['start_line'] = line_number
            self.current_path.end_line = line_number - 1
            print('finished calculating a path with',
                  len(self.current_path.points_x), 'points')
            if len(self.current_path.points_x) == 2:
                if not (self.current_path.points_x[0]
                        == self.current_path.points_x[1]
                        and self.current_path.points_y[0]
                        == self.current_path.points_y[1]):
                    self.complete_paths.append(self.current_path)
            if len(self.current_path.points_x) >= 3:
                self.complete_paths.append(self.current_path)
            self.current_path = Path(**params)

        f = re.search(r"F(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
        if f:
            self.feed_rate = float(f.groups()[0])*self.unit_factor

        # call the correct handling function to populate the path
        if self.current_path.move_type == MOVE_TYPE['RAPID']:
            self._handle_line(command, rapid=True)
        elif self.current_path.move_type == MOVE_TYPE['LINEAR']:
            self._handle_line(command, rapid=False)
        elif self.current_path.move_type == MOVE_TYPE['ARC_CW']:
            self._handle_arc(command, clockwise=True)
        elif self.current_path.move_type == MOVE_TYPE['ARC_CCW']:
            self._handle_arc(command, clockwise=False)

        return self.current_path

    def _handle_line(self, command, rapid=True):
        try:
            last_x = self.current_path.points_x[-1]
            last_y = self.current_path.points_y[-1]
            xTarget = last_x
            yTarget = last_y

            x = re.search(r"X(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
            if x:
                xTarget = float(x.groups()[0])*self.unit_factor
                if not self.absolute_steps:
                    xTarget += last_x
            y = re.search(r"Y(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
            if y:
                yTarget = float(y.groups()[0])*self.unit_factor
                if not self.absolute_steps:
                    yTarget += last_y

            path_len = math.sqrt((xTarget-last_x)**2+(yTarget-last_y)**2)
            self.job_duration += path_len / self.feed_rate
            self.max_x = max(self.max_x, xTarget)
            self.max_y = max(self.max_y, yTarget)
            self.min_x = min(self.min_x, xTarget)
            self.min_y = min(self.min_y, yTarget)

            if not (self.current_path.points_x[-1] == xTarget and
                    self.current_path.points_y[-1] == yTarget):
                self.current_path.points_x.append(xTarget)
                self.current_path.points_y.append(yTarget)
        except ValueError:
            _log.error('could not plot -> '+command)

    def _handle_arc(self, command, clockwise=True):
        '''
        drawArc draws an arc using the previous command as the start point, the
        xy coordinates from the current command as the end point, and the i, j
        coordinates from the current command as the circle center. Clockwise or
        counter-clockwise travel is based on the command.
        '''
        last_x = self.current_path.points_x[-1]
        last_y = self.current_path.points_y[-1]

        xTarget = last_x
        yTarget = last_y
        iTarget = 0.00
        jTarget = 0.00

        # pull values from the command
        x = re.search(r"X(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
        if x:
            xTarget = float(x.groups()[0])*self.unit_factor
            if not self.absolute_steps:
                xTarget += last_x
        y = re.search(r"Y(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
        if y:
            yTarget = float(y.groups()[0])*self.unit_factor
            if not self.absolute_steps:
                yTarget += last_y
        i = re.search(r"I(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
        if i:
            iTarget = float(i.groups()[0])*self.unit_factor
        j = re.search(r"J(?=.)(([ ]*)?[+-]?(\d*)(\.(\d+))?)", command)
        if j:
            jTarget = float(j.groups()[0])*self.unit_factor

        # calculate required points
        radius = math.sqrt(iTarget**2 + jTarget**2)
        centerX = last_x + iTarget
        centerY = last_y + jTarget
        angle1 = math.atan2(last_y-centerY, last_x-centerX)
        angle2 = math.atan2(yTarget - centerY, xTarget - centerX)

        # atan2 returns -pi to +pi but we want results from 0 - 2pi
        if angle1 < 0:
            angle1 = angle1 + 2*math.pi
        if angle2 < 0:
            angle2 = angle2 + 2*math.pi

        if clockwise:
            if angle1 < angle2:
                angle1 = angle1 + 2*math.pi
            direction = -1
        else:
            if angle2 < angle1:
                angle2 = angle2 + 2*math.pi
            direction = 1

        arcLen = abs(angle1 - angle2)
        if abs(angle1 - angle2) == 0:
            arcLen = 2*math.pi

        self.job_duration += arcLen / self.feed_rate

        curLen = 0.0
        while abs(curLen) < arcLen:
            xPosOnLine = centerX + radius*math.cos(angle1 + curLen)
            yPosOnLine = centerY + radius*math.sin(angle1 + curLen)
            curLen += direction * arcLen/25

            self.max_x = max(self.max_x, xTarget)
            self.max_y = max(self.max_y, yTarget)
            self.min_x = min(self.min_x, xTarget)
            self.min_y = min(self.min_y, yTarget)

            # if absolute_steps, only add points is they changed enough
            if self.absolute_steps:
                if not (
                    math.isclose(
                        self.current_path.points_x[-1], xPosOnLine,
                        abs_tol=0.001)
                    and math.isclose(
                        self.current_path.points_y[-1], yPosOnLine,
                        abs_tol=0.001)):
                    self.current_path.points_x.append(xPosOnLine)
                    self.current_path.points_y.append(yPosOnLine)
            else:
                self.current_path.points_x.append(xPosOnLine)
                self.current_path.points_y.append(yPosOnLine)
