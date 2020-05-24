# setup the environment
python -m venv venv
./venv/bash/python -m pip install --editable .
# on Windows do: .\venv\Scripts\python -m pip install --editable .

# set to autostart at boot
# ...

# set to mount any usb to the gcode directory
# using https://github.com/rbrito/usbmount
#sudo apt install usbmount
#set UM_MOUNTPOINT "/home/pi/gcode_files"
#set UM_MOUNTOPTIONS "readonly"