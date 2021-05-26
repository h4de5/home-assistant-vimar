"""Vimar Platform example without HA."""
# import async_timeout
import os
import sys
import configparser
import argparse

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


def main():

    parser = argparse.ArgumentParser(description='Command line client for controlling a vimar webserver')
    parser.add_argument('-c', '--config', type=str, default="credentials.cfg", dest="configpath", help="Path to your credentials settings")
    parser.add_argument('-p', '--platform', type=str, dest="platform", help="Must be one of: lights, covers, switches, climates, media_players, scenes or sensors")
    # parser.add_argument('-l', '--list', action='store_true', dest="list", help="List all available devices found in the given platform")
    parser.add_argument('-d', '--device', type=int, dest="device_id", help="ID of the device you want to change")
    parser.add_argument('-s', '--status', type=str, dest="status_name", help="Status that you want to change")
    parser.add_argument('-v', '--value', type=str, dest="target_value", help="Change status to the given value")
    args = parser.parse_args()

    if os.path.isfile("credentials.cfg") is False:
        print("credentials not found - please rename credentials.cfg.dist to credentials.cfg and adapt the settings.")
        exit(1)

    # read credentials from config files
    config = configparser.ConfigParser()
    config.read(args.configpath)
    config.sections()

    # setup link to vimar web server
    vimarconnection = VimarLink(
        config['webserver']['schema'],
        config['webserver']['host'],
        int(config['webserver']['port']),
        config['webserver']['username'],
        config['webserver']['password'],
        config['webserver']['certificate'],
        int(config['webserver']['timeout']))

    # if certificate is not available, download it
    if os.path.isfile(config['webserver']['certificate']) is False:
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

    # check all available platforms
    if args.platform is None:
        for device_type, platform in AVAILABLE_PLATFORMS.items():
            device_count = vimarproject.platform_exists(device_type)
            if device_count:
                print("found platform %s with %d %s" % (platform, device_count, device_type))
        exit(0)

    # get all devices
    devices = vimarproject.get_by_device_type(args.platform)

    if not devices:
        print("No devices found for platform:", args.platform)
        exit(1)

    # list all available devices for given platform
    if not args.device_id:
        # list all lights and their status
        for device_id, device in devices.items():
            print(device_id, "-", device["object_name"], "available status:", list(device["status"].keys()))
        exit(0)

    # show single device
    if args.device_id:
        args.device_id = str(args.device_id)
        # if the default device_id is not available turn on the first found light
        if args.device_id not in devices:
            print("No device found with id:", args.device_id, "in platform", args.platform)
            exit(1)

        statusdict = devices.get(args.device_id)["status"]
        print(args.device_id, "-", devices.get(args.device_id)["object_name"], "available status:", [key + ": " + value['status_value'] for key, value in statusdict.items()])

        if args.status_name:
            if args.status_name not in devices[args.device_id]["status"]:
                print("given device does not support '", args.status_name, "' status")
                exit(1)

            optionals = vimarconnection.get_optionals_param(args.status_name)

            if args.target_value:
                print("Setting", args.status_name, "to", args.target_value)
                vimarconnection.set_device_status(statusdict[args.status_name]["status_id"], args.target_value, optionals)


if __name__ == "__main__":
    main()