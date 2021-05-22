"""Vimar Platform example without HA."""
# import async_timeout
import os
import sys
import time

# those imports only work in that directory
# this will be easier to use, as soon as we have a separate python package
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
from custom_components.vimar.vimarlink.vimarlink import (VimarLink, VimarProject)

AVAILABLE_PLATFORMS = {
    "lights": 'light',
    "covers": 'cover',
    "switches": 'switch',
    "climates": 'climate',
    "media_players": 'media_player',
    "scenes": 'scene',
    "sensors": 'sensor',
}

# initialize credentials
# CHANGE YOUR CREDENTIALS HERE
schema = 'https'
host = '192.168.0.100'
port = 443
username = 'admin'
password = 'password'
certificate = 'rootCA.VIMAR.crt'
timeout = 5

# setup link to vimar web server
vimarconnection = VimarLink(schema, host, port, username, password, certificate, timeout)

# if certificate is not available, download it
if os.path.isfile(certificate) is False:
    vimarconnection.install_certificate()

# initialize project
vimarproject = VimarProject(vimarconnection)

# try to login
try:
    valid_login = vimarconnection.check_login()
except BaseException as err:
    print("Login Exception: %s" % err)
    valid_login = False

if (not valid_login):
    print("Login failed")
    exit(1)

# load all devices and device status
vimarproject.update()

# check all available device types
for device_type, platform in AVAILABLE_PLATFORMS.items():
    device_count = vimarproject.platform_exists(device_type)
    if device_count:
        print("load platform %s with %d %s" % (platform, device_count, device_type))

# get all lights
lights = vimarproject.get_by_device_type("lights")

# list all lights and their status
for device_id, device in lights.items():
    print(device_id, "-", device["object_name"], "available status:", list(device["status"].keys()))

# SELECT YOUR OWN DEVICE ID FROM THE LIST ABOVE
test_device_id = "704"

# if the default device_id is not available turn on the first found light
if (test_device_id not in lights):
    test_device_id = list(lights)[0]

if ("on/off" not in lights[test_device_id]["status"]):
    print("given device does not support 'on/off' status - available:", list(lights[test_device_id]["status"].keys()))
    exit(1)

# get optionals parameter for given status name
optionals = vimarconnection.get_optionals_param("on/off")

# change a single status to on
print("Turn on device", test_device_id, "-", lights[test_device_id]["object_name"])
vimarconnection.set_device_status(lights[test_device_id]["status"]["on/off"]["status_id"], '1', optionals)

# wait 2 seconds
time.sleep(2)

# change a single status to off again
print("Turn off device", test_device_id, "-", lights[test_device_id]["object_name"])
vimarconnection.set_device_status(lights[test_device_id]["status"]["on/off"]["status_id"], '0', optionals)
