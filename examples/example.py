"""Vimar Platform example without HA."""
# import async_timeout
import os
import configparser
import argparse
import xml.etree.cElementTree as xmlTree

# those imports only work in that directory
# this will be easier to use, as soon as we have a separate python package
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(CURRENT_DIR))
# from custom_components.vimar.vimarlink.vimarlink import (VimarLink, VimarProject)
from vimarlink.vimarlink import (VimarLink, VimarProject)

AVAILABLE_PLATFORMS = {
    "lights": 'light',
    "covers": 'cover',
    "switches": 'switch',
    "climates": 'climate',
    "media_players": 'media_player',
    "scenes": 'scene',
    "sensors": 'sensor',
}


def parse_var(s):
    """
    Parse a key, value pair, separated by '='
    That's the reverse of ShellArgs.

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"
    """
    items = s.split('=')
    key = items[0].strip()  # we remove blanks around keys, as is logical
    if len(items) > 1:
        # rejoin the rest:
        value = '='.join(items[1:])
    return (key, value)


def parse_vars(items):
    """
    Parse a series of key-value pairs and return a dictionary
    """
    d = {}

    if items:
        for item in items:
            key, value = parse_var(item)
            d[key] = value
    return d


def main():

    parser = argparse.ArgumentParser(description='Command line client for controlling a vimar webserver')
    parser.add_argument('-c', '--config', type=str, default="credentials.cfg", dest="configpath", help="Path to your credentials settings")
    parser.add_argument('-p', '--platform', type=str, dest="platform", help="Must be one of: lights, covers, switches, climates, media_players, scenes or sensors")
    # parser.add_argument('-l', '--list', action='store_true', dest="list", help="List all available devices found in the given platform")
    parser.add_argument('-d', '--device', type=int, dest="device_id", help="ID of the device you want to change")
    parser.add_argument('-s', '--status', type=str, dest="status_name", help="Status that you want to change")
    parser.add_argument('-v', '--value', type=str, dest="target_value", help="Change status to the given value")
    parser.add_argument('statuslist', metavar="status=value", type=str, nargs="*", help="Change the given status to the value")
    args = parser.parse_args()

    if os.path.isfile("credentials.cfg") is False:
        print("credentials not found - please rename credentials.cfg.dist to credentials.cfg and adapt the settings.")
        exit(1)

    # read credentials from config files
    config = configparser.ConfigParser()
    config.read(args.configpath)
    config.sections()

    print("Config ready")

    # setup link to vimar web server
    vimarconnection = VimarLink(
        config['webserver']['schema'],
        config['webserver']['host'],
        int(config['webserver']['port']),
        config['webserver']['username'],
        config['webserver']['password'],
        config['webserver']['certificate'],
        int(config['webserver']['timeout']))

    print("Link ready")

    # if certificate is not available, download it
    if os.path.isfile(config['webserver']['certificate']) is False:
        vimarconnection.install_certificate()
        print("Certificate ready")

    # initialize project
    vimarproject = VimarProject(vimarconnection)

    print("Project ready")

    # TODO - save and reuse session login
    # if os.path.isfile("session.pid"):
    #     file = open("session.pid", "r")
    #     VimarLink._session_id = file.readline()
    #     print("Loading session %s" % VimarLink._session_id)

    # try to login
    try:
        valid_login = vimarconnection.check_login()
    except BaseException as err:
        print("Login Exception: %s" % err)
        valid_login = False
    if (not valid_login):
        print("Login failed")
        exit(1)

    # TODO - save and reuse session login
    # xml = vimarconnection.check_session()
    # logincode = xml.find('userName')
    # loginmessage = xml.find('userID')
    # print("found user data:", xmlTree.tostring(xml, method='xml'), logincode.text, loginmessage.text)
    # # if logincode.text is None:
    # # VimarLink._session_id = None

    # try:
    #     file = open("session.pid", "w")
    #     file.write(VimarLink._session_id)
    #     file.close()

    # except IOError as err:
    #     print("Saving session.pid failed: %s" % err)

    print("Logged in")

    # load all devices and device status
    vimarproject.update()

    print("Devices loaded")

    # check all available platforms
    if args.platform is None:
        for device_type, platform in AVAILABLE_PLATFORMS.items():
            device_count = vimarproject.platform_exists(device_type)
            if device_count:
                print("found platform %s with %d %s" % (platform, device_count, device_type))
        exit(0)

    # get all devices
    devices = vimarproject.get_by_device_type(args.platform)

    print("Devices parsed")

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

        statuslist = None
        if args.statuslist:
            statuslist = parse_vars(args.statuslist)

        if args.status_name and args.target_value:
            statuslist = {args.status_name: args.target_value}

        statusdict = devices.get(args.device_id)["status"]
        print(args.device_id, "-", devices.get(args.device_id)["object_name"], "available status:",
              [key + " #" + value['status_id'] + ": " + value['status_value'] for key, value in statusdict.items()])

        if statuslist:
            for status_name, status_value in statuslist.items():
                if status_name not in devices[args.device_id]["status"]:
                    print("given device does not support '", status_name, "' status")
                    exit(1)

            for status_name, status_value in statuslist.items():
                optionals = vimarconnection.get_optionals_param(status_name)
                vimarconnection.set_device_status(statusdict[status_name]["status_id"], status_value, optionals)

if __name__ == "__main__":
    main()
