# Laserinterface

**The only graphical interface for GRBL lasercutters that implements the GPIO functionalities of an embedded Raspberry Pi.**

LaserInterface was created with the goal of a **touchscreen controlled** Laser Cutter that does not requere an external PC. You simply plug a USB drive into the machine, use the touchscreen to setup the origin etc, and fire away. Now, there are already a ton of gcode senders, a lot of which also run on a raspberry pi, but none of them use the GPIO functionality to ensure the machine runs savely or to control parts of the machine.

LaserInterface works by having a relay board connected to the GPIO buttons for controls; and a thermometer, switches, and sersors for the inputs. Of course you can control them manually, but you can **configure automated callbacks** too. Like pausing grbl when the laser tube gets too hot or if a door is opened; or bind the power of the air assist and the laser so it only makes noise during a job.

Using the GPIO is not the only thing LaserInterface can do. You can select a program with a preview of the path, size, and duration. You can jog the machine around to set working offsets and fire testpulses.

## Screenshots

| Start/monitor/control jobs         | Jog the machine                  |
| ---------------------------------- | -------------------------------- |
| ![pic](docs/pics/screen_home.png)  | ![pic](docs/pics/screen_jog.png) |
| ---------------------------------- | -------------------------------- |
| Select and preview a job           | control and monitor GPIO         |
| ---------------------------------- | -------------------------------- |
| ![pic](docs/pics/screen_files.png) | ![pic](docs/pics/screen_jog.png) |

## Installing LaserInterface

Use the modified kivypi image on a raspberry pi, available at the releases page. *(coming up)*
If you use different hardware then download the source code and set this to auto start at bootup. *(need to add list of commands)*

## Configuring LaserInterface

Changing the settings can be done by modifying `data/config.yaml`.

## Starting LaserInterface

For the best embedded experience, LaserInterface should start at bootup. Official releases *(The planned kivypi image)* are set up for this. During development you can run the program using the start programs or by running LaserInterface as a python module. On linux thats done using `./.venv/bash/python -m laserinterface` and on windows using `./.venv/Scripts/python.exe -m laserinterface`.

## Further development

Short term improvements:

- [ ] set up a list of command for a raspberry pi (start at boot; mount usb in gcode folder; system read only?;)
- [ ] Release a completely set up image for the raspberry pi
- [ ] Add Settings menu to change the config.yaml file
- [ ] Add callbacks for starting/stoping a job
- [ ] Fix the virtual keyboard

Planned features:

- [ ] Support for reading SVG and converting to gcode
- [ ] Support for reading png/jpg and converting to engrave job
- [ ] Implement boxes.py for integrated boxes creation

### Reusing part of the software

The code is split up over modules that share datamanagers to pass data. It should be fairly easy to reuse only a single submodule in your code but most ui elements do depend on the helpers and datamanagers modules. So if you are getting errors while running individual modules, this should be the first place to look.
