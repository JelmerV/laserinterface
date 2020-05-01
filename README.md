# Laserinterface

**The only graphical interface for GRBL lasercutters that implements the GPIO functionalities of an embedded Raspberry Pi.**

## Installing LaserInterface

Use the modified kivypi image on a raspberry pi, available at the releases page. *(Not yet, but is planned)*
If you use different hardware then download the source code and set this to auto start at bootup.

## Configuring LaserInterface

Changing the settings can be done by modifying `data/config.yaml`.

## Starting LaserInterface

For the best embedded experience, LaserInterface should start at bootup. Official releases *(The planned kivypi image)* are set up for this. During development you can run the program using the start programs or by running LaserInterface as a python module. On linux thats done using `./.venv/bash/python -m laserinterface` and on windows using `./.venv/Scripts/python.exe -m laserinterface`.

## Using LaserInterface

*(TODO: Add some screenshots)*

## Further development

TODO:

- [ ] Sending gcode is not fast enough
- [ ] implement the configuration for automated gpio actions

### Reusing part of the software

I have tried my best to set the software up modular. This should make it easier to find where a bug is coming from and also makes it easier to understand the code that is causing it. You may want to reuse only a single submodule in your code. That should be fairly easy to implement. Some classes do depend on the helpers and datamanager. So if you are getting error while running individual modules, those should be the first place to look.
