import re
import time
import logging
from threading import Thread

from laserinterface.datamanager.machine import MachineStateManager
from laserinterface.datamanager.terminal import TerminalManager

from laserinterface.helpers.grblinterface import GrblInterface

from laserinterface.data.grbl_doc import COMMANDS

logging.basicConfig()
_log = logging.getLogger(__name__)


trim_decimal = 3
selected_file = r'D:\home\pi\gcode_files\palmtree.nc'


mach_state = MachineStateManager()
terminal = TerminalManager()
grbl_com = GrblInterface(terminal=terminal, machine_state=mach_state)
if not grbl_com.connect():
    raise(Exception, 'could not connect')
time.sleep(1)

_quit = False
job_active = False

for i in range(10):
    grbl_com.serial_send(COMMANDS['feed +10'])


def checker():
    while not _quit:
        if job_active and mach_state.grbl_status.get('state') == 'Idle':
            print('next lines:', grbl_com.lines_to_sent.queue)
            s = 'Sending too slow:\n'
            for line in terminal.get_all_lines()[-10:]:
                s += f"\t{'  '.join([str(i) for i in line])}\n"
            print(s)
            print('lines in send buffer = ', len(terminal.line_out_buffer))
            print('lines at grbl buffer = ', len(terminal.line_wait_for_ok))
            print('chars in grbl buffer:', sum(grbl_com.chars_in_buffer.queue))
            print('')
            time.sleep(0.2)
        time.sleep(0.01)


Thread(target=checker, daemon=True).start()


with open(selected_file, 'r') as file:
    lines = file.readlines()

total_lines = len(lines)
print(f'need to send {total_lines} lines')

a = 0.0
b = 0.0
c = 0.0
d = 0.0
e = 0.0

count = 0
job_active = True
job_start_time = time.time()
start_time = time.time()
for line in lines:
    line = line.strip().upper()

    print(f'a took: {time.time()-start_time}')
    a += time.time()-start_time
    start_time = time.time()

    # trim decimals:
    if trim_decimal:
        line = re.sub(r'(\w[+-]?\d+\.\d{'+str(trim_decimal)+r'})\d+',
                      r'\1', line)

    print(f'b took: {time.time()-start_time}')
    b += time.time()-start_time
    start_time = time.time()

    # store comments to terminal
    comments = re.search(r'\((.*?)\)|;(.*)', line)
    if comments:
        terminal.store_comment(comments.group(0))
        print(f'################# {comments.group(0)}')

    print(f'c took: {time.time()-start_time}')
    c += time.time()-start_time
    start_time = time.time()

    # Strip spaces and comments (**) and ;**
    line = re.sub(r'\+|\s|\(.*?\)|;.*', '', line)

    print(f'd took: {time.time()-start_time}')
    d += time.time()-start_time
    start_time = time.time()

    if line == '':
        continue

    # send line but wait when the buffer is full
    grbl_com.serial_send(line, blocking=True)
    count += 1

    print(f'e took: {time.time()-start_time}')
    e += time.time()-start_time
    start_time = time.time()
    print(f'*** line send = {line}\n')

print(f'total time at a: {a} sec')
print(f'total time at b: {b} sec')
print(f'total time at c: {c} sec')
print(f'total time at d: {d} sec')
print(f'total time at e: {e} sec')

# wait unltil all commands are handled
while len(terminal.line_wait_for_ok) > 0:
    time.sleep(0.1)

job_active = False
_quit = True


print(f'finished sending "{selected_file}"')
print(f'job took {time.time()-job_start_time} seconds')
